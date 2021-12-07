from ortools.sat.python import cp_model


def main():
    # Example data
    num_nurses = 4
    num_shifts = 3
    num_days = 3

    all_nurses = range(num_nurses)
    all_shifts = range(num_shifts)
    all_days = range(num_days)

    # Create the model
    model = cp_model.CpModel()

    # Problem variables
    shifts = {}  # dict: tuple: model.NewBoolVar(); equals 1 if a nurse is assigned and 0 otherwise
    for n in all_nurses:
        for d in all_days:
            for s in all_shifts:
                shifts[(n, d, s)] = model.NewBoolVar(f'shift_n{n}d{d}s{s}')

    # Assign nurses to shifts
    # Constraints:
    #   1) each shift is assigned to a single nurse per day
    #   2) each nurse works at most one shift per day

    # 1
    # in each day and in each shift, the sum of all nurses working is equal to 1
    for d in all_days:
        for s in all_shifts:
            model.Add(sum(shifts[(n, d, s)] for n in all_nurses) == 1)

    # 2
    # in each day, each nurse works AT MOST one shift (i.e. could have a day off)
    for n in all_nurses:
        for d in all_days:
            model.Add(sum(shifts[(n, d, s)] for s in all_shifts) <= 1)

    # Assign shifts as evenly as possible
    # Try to distribute the shifts evenly, so that each nurse works
    # min_shifts_per_nurse shifts. If this is not possible, because the total
    # number of shifts is not divisible by the number of nurses, some nurses will
    # be assigned one more shift.
    min_shifts_per_nurse = (num_shifts * num_days) // num_nurses
    if num_shifts * num_days % num_nurses == 0:
        max_shifts_per_nurse = min_shifts_per_nurse
    else:
        max_shifts_per_nurse = min_shifts_per_nurse + 1

    for n in all_nurses:
        num_shifts_worked = []  # list for summation of number of shifts worked per nurse
        for d in all_days:
            for s in all_shifts:
                num_shifts_worked.append(shifts[(n, d, s)])
        model.Add(min_shifts_per_nurse <= sum(num_shifts_worked))
        model.Add(sum(num_shifts_worked) <= max_shifts_per_nurse)

    # Solver - non-optimization problem
    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 0
    solver.parameters.enumerate_all_solutions = True


    # Register a solution callback called at each solution
    class NursesPartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
        def __init__(self, shifts, num_nurses, num_days, num_shifts, limit):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self._shifts = shifts
            self._num_nurses = num_nurses
            self._num_days = num_days
            self._num_shifts = num_shifts
            self._solution_count = 0
            self._solution_limit = limit

        def on_solution_callback(self):
            self._solution_count += 1
            print('Solution %i' % self._solution_count)
            for d in range(self._num_days):
                print('Day %i' % d)
                for n in range(self._num_nurses):
                    is_working = False
                    for s in range(self._num_shifts):
                        if self.Value(self._shifts[(n, d, s)]):
                            is_working = True
                            print('  Nurse %i works shift %i' % (n, s))
                    if not is_working:
                        print('  Nurse {} does not work'.format(n))
            if self._solution_count >= self._solution_limit:
                print('Stop search after %i solutions' % self._solution_limit)
                self.StopSearch()

        def solution_count(self):
            return self._solution_count

    # Display the first five solutions.
    solution_limit = 5
    solution_printer = NursesPartialSolutionPrinter(shifts, num_nurses,
                                                    num_days, num_shifts,
                                                    solution_limit)
    # run
    solver.Solve(model, solution_printer)

if __name__ == '__main__':
    main()