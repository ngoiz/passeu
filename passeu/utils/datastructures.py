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
