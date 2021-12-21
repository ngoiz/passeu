from ortools.sat.python import cp_model
import sys
sys.path.append('../passeu/')
import passeu.utils.constraints as constraints
from absl import app
from absl import flags
from google.protobuf import text_format

FLAGS = flags.FLAGS

flags.DEFINE_string('output_proto', '',
                    'Output file to write the cp_model proto to.')
flags.DEFINE_string('params', 'max_time_in_seconds:10.0',
                    'Sat solver parameters.')

# DATA STRUCTURES
class Employee:
    num_employees = 0  # class counter

    def __init__(self, name, contract_weekly_hours):
        self.name = name
        self.id = Employee.num_employees
        self.contract_weekly_hours = contract_weekly_hours

        Employee.num_employees += 1  # update counter

        self.schedule = None


# PROBLEM DATA
class ShopData:
    shifts = ['O', 'M', 'A', 'C']  # Off, Morning, Afternoon, Closing
    days = ['M', 'T', 'W', 'Th', 'F', 'St', 'Sn']

    def __init__(self):

        # daily demands for work shifts (morning, afternon, night) for each day
        # of the week starting on Monday. HEADCOUNT
        self.weekly_cover_demands = [
            (2, 3, 1),  # Monday
            (2, 3, 1),  # Tuesday
            (2, 2, 2),  # Wednesday
            (2, 3, 1),  # Thursday
            (2, 2, 2),  # Friday
            (1, 2, 3),  # Saturday
            (1, 3, 1),  # Sunday
        ]

        # Sum of all employee working hours for each day of the week
        self.daily_manhour_targets = [
            40,  # monday
            40,  # tuesday
            40,  # wednesday
            40,  # thurs
            40,  # fri
            40,  # sat
            40,  # sun
        ]

        # Fixed assignments (employee_id, shift, day)
        self.fixed_assignments = [
            (3, 0, 0)
        ]

    @property
    def num_days(self):
        # In case we need it later
        return 7

    @property
    def num_shifts(self):
        return len(self.shifts)

    @property
    def num_weeks(self):
        return 1


def solve_shift_scheduling(params, output_proto):
    # INPUT DATA
    shop_data = ShopData()
    employees = []
    employees.extend([
        Employee('Logan', 40),
        Employee('Dass', 40),
        Employee('Curro', 40),
        Employee('Dakota', 30),
        Employee('Turco', 40),
        Employee('Duque', 40),
        Employee('Marque', 40),
        # Employee('Turco2', 40),
        # Employee('Duque2', 40),
        # Employee('Marque2', 40)
    ]
    )
    # build from Employee data
    # Request: (employee, shift, day, weight)
    # A negative weight indicates that the employee desire this assignment.
    requests = [
        (0, 0, 1, -2)  # Logan wants tuesday off
    ]
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
        for s in range(shop_data.num_shifts):
            for d in range(shop_data.num_days):
                work_hours[e, s, d] = model.NewIntVarFromDomain(domain=domain,
                                                                name=f'workhours{e}_{s}_{d}')

    # Linear terms of the objective in a minimization context.
    obj_int_vars = []
    obj_int_coeffs = []
    obj_bool_vars = []
    obj_bool_coeffs = []

    # Exactly one shift per day.
    for e in range(num_employees):
        for d in range(shop_data.num_days):
            model.Add(sum(work[e, s, d] for s in range(shop_data.num_shifts)) == 1)

    # TODO: need to add not also boolean on employee working but also for how long

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

    # # Max weekly hours constraint
    # maybe add AND constraint, like works AND work_hours > 0
    # for e in range(num_employees):
    #     for s in range(shop_data.num_shifts):
    #         working_hours = [work_hours[e, s, d] for d in range(shop_data.num_days)]
    #         hard_min = employees[e].contract_weekly_hours
    #         hard_max = hard_min
    #         variables, coeffs = constraints.add_soft_sum_constraint(
    #             model, working_hours,
    #             hard_min, hard_min, 0,
    #             hard_max, hard_max, 0,
    #             f'weekly_hours_constraint(employee{e}, shift{s}, week{w}'
    #         )
    #         obj_int_vars.extend(variables)
    #         obj_int_coeffs.extend(coeffs)


    # Link off shifts and 0 hours
    for e in range(num_employees):
        for d in range(shop_data.num_days):
            # model.AddImplication(work[(e, 0, d)].IsEqualTo(1), work_hours[(e, 0, d)].IsEqualTo(0))
            # model.Add(ct)
            # model.AddBoolAnd([work[(e, 0, d)], work_hours[e, 0, d].IsEqualTo(1)])
            pass
            model.Add(work_hours[e, 0, d] == 0)
            # model.AddBoolAnd([work[e, ]])
            for s in range(1, shop_data.num_shifts):
                model.Add(work_hours[e, s, d] != 0)
                # model.AddBoolOr([work[(e, s, d)].Not(), work_hours[(e, s, d)].IsEqualTo(0)])
                # new_var = model.NewBoolVar()
                # model.AddBoolAnd([new_var, work[(e, s, d)]])
                # model.AddImplication(work[(e, s, d)].Not(), work_hours[(e, s, d)].IsEqualTo(0))
                pass
                # model.AddImplication(work[(e, s, d)].Not(), work_hours[(e, s, d)].IsEqualTo(6))
                # model.AddImplication(work[(e, 0, d)].IsEqualTo(1), work_hours[(e, s, d)].IsEqualTo(0))
                # model.AddImplication(work[(e, s, d)].IsEqualTo(0), work_hours[(e, s, d)].IsEqualTo(0))
                # import pdb; pdb.set_trace()
                # model.AddImplication(work_hours[(e, s, d)].IsEqualTo(0), work[(e, s, d)].Not())
                # model.AddBoolAnd([work[(e, 0, d)].IsEqualTo(1), work_hours[(e, 0, d)].IsEqualTo(0)])



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
        header = '          '
        for w in range(shop_data.num_weeks):
            header += 'M T W T F S S '
        print(header)
        for e in range(num_employees):
            schedule = ''
            for d in range(shop_data.num_days):
                for s in range(shop_data.num_shifts):
                    works = solver.BooleanValue(work[e, s, d])
                    # print(works, hours)
                    if works:
                        hours = solver.Value(work_hours[e, s, d])
                        schedule += shop_data.shifts[s] + f'({hours})' + ' '
            print(f'{employees[e].name} (id={e}): {schedule}')
        print()
        import pdb; pdb.set_trace()
        print('Total Employee hours:')
        for e in range(num_employees):
            employee_hours = 0
            for d in range(shop_data.num_days):
                for s in range(shop_data.num_shifts):
                    if solver.BooleanValue(work[e, s, d]):
                        employee_hours += solver.Value(work_hours[e, s, d])
            print(f'{employees[e].name} (id={e}): {employee_hours} hrs (max {employees[e].contract_weekly_hours} hrs)')
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