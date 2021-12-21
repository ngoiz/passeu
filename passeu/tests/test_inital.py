from ortools.sat.python import cp_model

from absl import app
from absl import flags

FLAGS = flags.FLAGS


# DATA STRUCTURES
class Employee:
    num_employees = 0  # class counter

    def __init__(self, name, contract_weekly_hours):
        self.name = name
        self.id = Employee.num_employees
        self.contract_weekly_hours = contract_weekly_hours

        Employee.num_employees += 1  # update counter


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
        return 3

# INPUT DATA
shop_data = ShopData()
employees = []
employees.extend([
    Employee('Logan', 40),
    Employee('Dass', 40),
    Employee('Curro', 40),
    Employee('Dakota', 32),
]
)
num_employees = len(employees)


# CONSTRAINTS

# Shift constraints on continuous sequence :
#     (shift, hard_min, soft_min, min_penalty,
#             soft_max, hard_max, max_penalty)
shift_constraints = [
    # One or two consecutive days of rest (shift 0), this is a hard constraint.
    (0, 1, 1, 0, 2, 2, 0),
    # betweem 2 and 3 consecutive days of night shifts, 1 and 4 are
    # possible but penalized.
    (3, 1, 2, 20, 3, 4, 5),
]

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
    (2, 3, 1),  # Monday
    (2, 3, 1),  # Tuesday
    (2, 2, 2),  # Wednesday
    (2, 3, 1),  # Thursday
    (2, 2, 2),  # Friday
    (1, 2, 3),  # Saturday
    (1, 3, 1),  # Sunday
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



if __name__ == '__main__':
    print('Running...')
    import pdb; pdb.set_trace()