from ortools.sat.python import cp_model
import sys
import passeu.utils.constraints as constraints
from absl import app
from absl import flags
from google.protobuf import text_format
from passeu.utils.datastructures import Employee, ShopData, EmployeeData

FLAGS = flags.FLAGS

flags.DEFINE_string('output_proto', '',
                    'Output file to write the cp_model proto to.')
flags.DEFINE_string('params', 'max_time_in_seconds:10.0',
                    'Sat solver parameters.')

# DATA STRUCTURES

def solve_shift_scheduling(params, output_proto):
    # INPUT DATA
    shop_data = ShopData()
    employees = []
    employees.extend([
        Employee('Logan', 32, level=1, maximum_overtime=6),
        Employee('Dass', 40, level=1),
        Employee('Curro', 40),
        Employee('Dakota', 26),
        Employee('Turco', 40),
        Employee('Duque', 40, level=2),
        Employee('Marque', 40, level=2),
        # Employee('Turco2', 40),
        # Employee('Duque2', 40),
        # Employee('Marque2', 40)
    ]
    )
    shop_data.employee_data = EmployeeData()
    shop_data.employee_data.employees = employees
    shop_data.employee_data.levels = {0, 1, 2}
    levels = shop_data.employee_data.levels
    shop_data.employee_data.requests = [(0, 0, 1, -2)] # Logan wants tuesday off

    # build from Employee data
    # Request: (employee, shift, day, weight)
    # A negative weight indicates that the employee desire this assignment.
    # requests = [
    #     (0, 0, 1, -2)  # Logan wants tuesday off
    # ]
    requests = shop_data.employee_data.requests
    num_employees = len(employees)


    # CONSTRAINTS

    # Shift constraints on continuous sequence :
    #     (shift, hard_min, soft_min, min_penalty,
    #             soft_max, hard_max, max_penalty)
    shift_constraints = [
        # One or two consecutive days of rest (shift 0), this is a hard constraint.
        (0, 1, 1, 0, 3, 3, 0),  # changing to 3
        # betweem 2 and 3 consecutive days of night shifts, 1 and 4 are
        # possible but penalized.
        (3, 1, 2, 20, 3, 4, 5),
    ]

    # Weekly hour constraint: each employee hard min of contract hours, soft max contract hours
    # hard max overtime
    # (hard_min, soft_min, min_penalty, soft_max, hard_max, max_penalty)
    weekly_hour_constraints = []

    # Weekly sum constraints on shifts days:
    #     (shift, hard_min, soft_min, min_penalty,
    #             soft_max, hard_max, max_penalty)
    weekly_sum_constraints = [
        # Constraints on rests per week.
        (0, 2, 2, 7, 2, 3, 4),
        # At least 1 night shift per week (penalized). At most 4 (hard).
        (3, 0, 1, 3, 4, 4, 0),
    ]

    # Penalized transitions:
    #     (previous_shift, next_shift, penalty (0 means forbidden))
    penalized_transitions = [
        # Afternoon to night has a penalty of 4.
        (2, 3, 4),
        # Night to morning is forbidden.
        (3, 1, 0),
    ]

    # daily demands for work shifts (morning, afternoon, night) for each day
    # of the week starting on Monday.  TODO: change to hours?? -> Add a total worked hours soft constraint too
    weekly_cover_demands = [
        (1, 0, 1),  # Monday
        (1, 0, 1),  # Tuesday
        (1, 0, 2),  # Wednesday
        (1, 0, 1),  # Thursday
        (1, 0, 2),  # Friday
        (1, 0, 3),  # Saturday
        (1, 0, 1),  # Sunday
    ]

    # Employee level experience demands by day
    # (level0, level1, level2)
    daily_experience_demands = [
        (2, 1, 1),  # Monday
        (2, 1, 1),  #
        (2, 1, 1),  #
        (2, 1, 1),  #
        (2, 1, 1),
        (2, 2, 1),
        (2, 2, 1),
    ]

    # Penalty for exceeding the cover constraint per shift type.
    excess_cover_penalties = (2, 2, 5)

    model = cp_model.CpModel()

    # now need to add as variable to Employee class whether they work or not
    work = {}
    for e in range(num_employees):
        for s in range(shop_data.num_shifts):
            for d in range(shop_data.num_days):
                work[e, s, d] = model.NewBoolVar(f'work{e}_{s}_{d}')

    # shift duration
    work_hours = {}
    domain = cp_model.Domain.FromValues([0, 6, 8])
    for e in range(num_employees):
            for d in range(shop_data.num_days):
                work_hours[e, d] = model.NewIntVarFromDomain(domain=domain,
                                                            name=f'workhours{e}_{d}')

    # Linear terms of the objective in a minimization context.
    obj_int_vars = []
    obj_int_coeffs = []
    obj_bool_vars = []
    obj_bool_coeffs = []

    # Exactly one shift per day.
    for e in range(num_employees):
        for d in range(shop_data.num_days):
            model.Add(sum(work[e, s, d] for s in range(shop_data.num_shifts)) == 1)

    # Fixed assignments. Hard constraint
    for e, s, d in shop_data.fixed_assignments:
        model.Add(work[e, s, d] == 1)

    # Employee requests
    for e, s, d, w in requests:
        obj_bool_vars.append(work[e, s, d])
        obj_bool_coeffs.append(w)

    # Shift constraints
    for ct in shift_constraints:
        shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
        for e in range(num_employees):
            works = [work[e, shift, d] for d in range(shop_data.num_days)]
            variables, coeffs = constraints.add_soft_sequence_constraint(
                model, works, hard_min, soft_min, min_cost, soft_max, hard_max,
                max_cost,
                'shift_constraint(employee %i, shift %i)' % (e, shift))
            obj_bool_vars.extend(variables)
            obj_bool_coeffs.extend(coeffs)

    # Link off shifts and 0 hours
    for e in range(num_employees):
        for d in range(shop_data.num_days):
            model.Add(work_hours[(e, d)] == 0).OnlyEnforceIf(work[(e, 0, d)])

            # This one should not be needed once we add the summation of weekly hours constraints
            model.Add(work_hours[(e, d)] > 0).OnlyEnforceIf(work[(e, 0, d)].Not())

    # Max weekly working hours - currently a hard constraint to meet contract hours
    # max_daily_hours = constraints.ContractHours(shop_data)
    # max_daily_hours.apply(model, work_hours)

    max_weekly_hours = constraints.OvertimeContractHours(shop_data)
    vars, coeffs = max_weekly_hours.apply(model, work_hours, overtime_max_cost=5)
    obj_int_vars.extend(vars)
    obj_int_coeffs.extend(coeffs)

    # Weekly sum constraints
    for ct in weekly_sum_constraints:
        shift, hard_min, soft_min, min_cost, soft_max, hard_max, max_cost = ct
        for e in range(num_employees):
            for w in range(shop_data.num_weeks):
                works = [work[e, shift, d + w * 7] for d in range(7)]
                variables, coeffs = constraints.add_soft_sum_constraint(
                    model, works, hard_min, soft_min, min_cost, soft_max,
                    hard_max, max_cost,
                    'weekly_sum_constraint(employee %i, shift %i, week %i)' %
                    (e, shift, w))
                obj_int_vars.extend(variables)
                obj_int_coeffs.extend(coeffs)

    # # Daily experience requirements (and could be done per shift too but this example likely has too few employees)
    daily_experience = constraints.WorkerExperienceDay(shop_data)
    exp_vars, exp_coeffs = daily_experience.apply(model, work, daily_experience_demands=daily_experience_demands)
    obj_int_vars.extend(exp_vars)
    obj_int_coeffs.extend(exp_coeffs)

    # Penalized transitions
    for previous_shift, next_shift, cost in penalized_transitions:
        for e in range(num_employees):
            for d in range(shop_data.num_days - 1):
                transition = [
                    work[e, previous_shift, d].Not(), work[e, next_shift,
                                                           d + 1].Not()
                ]
                if cost == 0:
                    model.AddBoolOr(transition)
                else:
                    trans_var = model.NewBoolVar(
                        'transition (employee=%i, day=%i)' % (e, d))
                    transition.append(trans_var)
                    model.AddBoolOr(transition)
                    obj_bool_vars.append(trans_var)
                    obj_bool_coeffs.append(cost)


    # Cover constraints
    for s in range(1, shop_data.num_shifts):
        for w in range(shop_data.num_weeks):
            for d in range(7):
                works = [work[e, s, w * 7 + d] for e in range(num_employees)]
                # Ignore Off shift.
                min_demand = weekly_cover_demands[d][s - 1]
                worked = model.NewIntVar(min_demand, num_employees, '')
                model.Add(worked == sum(works))
                over_penalty = excess_cover_penalties[s - 1]
                if over_penalty > 0:
                    name = 'excess_demand(shift=%i, week=%i, day=%i)' % (s, w,
                                                                         d)
                    excess = model.NewIntVar(0, num_employees - min_demand,
                                             name)
                    model.Add(excess == worked - min_demand)
                    obj_int_vars.append(excess)
                    obj_int_coeffs.append(over_penalty)


    # Objective
    model.Minimize(
        sum(obj_bool_vars[i] * obj_bool_coeffs[i]
            for i in range(len(obj_bool_vars))) +
        sum(obj_int_vars[i] * obj_int_coeffs[i]
            for i in range(len(obj_int_vars))))

    if output_proto:
        print('Writing proto to %s' % output_proto)
        with open(output_proto, 'w') as text_file:
            text_file.write(str(model))

    # Solve the model.
    solver = cp_model.CpSolver()
    if params:
        text_format.Parse(params, solver.parameters)
    solution_printer = cp_model.ObjectiveSolutionPrinter()
    status = solver.Solve(model, solution_printer)

    # Print solution.
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print()
        header = 3*'\t'
        for w in range(shop_data.num_weeks):
            header += '\t'.join([f'{day}' for day in shop_data.days])
        print(header)
        for e in range(num_employees):
            schedule = ''
            for d in range(shop_data.num_days):
                for s in range(shop_data.num_shifts):
                    # hours = solver.Value(work_hours[e, s, d])
                    hours = solver.Value(work_hours[e, d])
                    works = solver.BooleanValue(work[e, s, d])
                    # print(f'Shift {s}', works, hours)
                    if works:
                        schedule += shop_data.shifts[s] + f'({hours})' + '\t'
            print(f'{employees[e].name} (id={e}, l={employees[e].level}):\t{schedule}')
        print()
        print('Total Employee hours:')
        for e in range(num_employees):
            employee_hours = 0
            for d in range(shop_data.num_days):
                for s in range(shop_data.num_shifts):
                    if solver.BooleanValue(work[e, s, d]):
                        employee_hours += solver.Value(work_hours[e, d])
            print(f'{employees[e].name} (id={e}): {employee_hours} hrs (max {employees[e].contract_weekly_hours} hrs)')
        print()
        print('Employee Experience per day')
        header = '\t\t' + '\t'.join([f'{day}' for day in shop_data.days])
        print(header)
        for l in levels:
            out_str = f'Level {l}:\t'
            for d in range(shop_data.num_days):
                working_employees_of_level = 0
                for e in range(num_employees):
                    if employees[e].level == l:
                        for s in range(1, shop_data.num_shifts):
                            if solver.BooleanValue(work[(e, s, d)]):
                                working_employees_of_level += 1
                out_str += f'{working_employees_of_level}/{daily_experience_demands[d][l]}\t'
            print(out_str)
        print()
        print('Penalties:')
        for i, var in enumerate(obj_bool_vars):
            if solver.BooleanValue(var):
                penalty = obj_bool_coeffs[i]
                if penalty > 0:
                    print('  %s violated, penalty=%i' % (var.Name(), penalty))
                else:
                    print('  %s fulfilled, gain=%i' % (var.Name(), -penalty))

        for i, var in enumerate(obj_int_vars):
            if solver.Value(var) > 0:
                print('  %s violated by %i, linear penalty=%i' %
                      (var.Name(), solver.Value(var), obj_int_coeffs[i]))

    print()
    print('Statistics')
    print('  - status          : %s' % solver.StatusName(status))
    print('  - conflicts       : %i' % solver.NumConflicts())
    print('  - branches        : %i' % solver.NumBranches())
    print('  - wall time       : %f s' % solver.WallTime())


def main(_):
    solve_shift_scheduling(FLAGS.params, FLAGS.output_proto)


if __name__ == '__main__':
    print('Running...')
    app.run(main)
    import pdb; pdb.set_trace()