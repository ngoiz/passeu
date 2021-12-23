import passeu.interface.interface as interface


class EmployeeData:

    def __init__(self, input_xls_file):

        self.input_file_xls = input_xls_file

        self.employees = None  # list(Employee)
        self.employee_lookup = None  # dict name:id

        self.requests = []

    @property
    def num_employees(self):
        return len(self.employees)

    def create_employee_data(self):
        employees_raw_data, self.employee_lookup = interface.create_employee_data(self.input_file_xls)

        self.employees = []
        for entry in employees_raw_data:
            self.employees.append(Employee(entry['name'],
                                           contract_weekly_hours=entry['contract_weekly_hours']))

    def create_requests(self, shop_data):
        # employee_name/id; shift; day; weight (negative is desire; positive is penalty)
        raw_requests = interface.create_request_list(self.input_file_xls)
        for entry in raw_requests:
            if type(entry[0]) is str:
                try:
                    employee_id = self.employee_lookup[entry[0]]
                except KeyError:
                    raise KeyError(f'Unable to find employee {entry[0]} in list of employees:'
                                   f'\n{self.employee_lookup.values()}')

            elif type(entry[0]) is int:
                employee_id = entry[0]
            else:
                raise TypeError('Employee must be either id or name')

            shift = shop_data.shift_mapping(entry[1])

            if type(entry[2]) is int:
                day = entry[2]
            else:
                raise TypeError(f'Day should be an integer and is {type(entry[2])}')

            if type(entry[3]) is int:
                weight = entry[3]
            else:
                raise TypeError(f'Day should be an integer and is {type(entry[3])}')

            self.requests.append((employee_id, shift, day, weight))


class Employee:
    num_employees = 0  # class counter

    def __init__(self, name, contract_weekly_hours, level=0):
        self.name = name
        self.id = Employee.num_employees
        self.contract_weekly_hours = contract_weekly_hours
        self.level = level

        Employee.num_employees += 1  # update counter

        self.schedule = None

    def __repr__(self):
        out_str = f'Employee({self.id},{self.name})\thours({self.contract_weekly_hours})'
        return out_str


# PROBLEM DATA
class ShopData:
    shift_full_name = ['Off', 'Morning', 'Afternoon', 'Close']
    shifts = [sn[0] for sn in shift_full_name]  # Off, Morning, Afternoon, Closing
    days = ['M', 'T', 'W', 'Th', 'F', 'St', 'Sn']

    def __init__(self, input_data_xls=None):
        self.input_data_xls = input_data_xls
        self.employee_data = None  # EmployeeData class

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

    def load_weekly_headcount_demand(self):
        self.weekly_cover_demands = interface.create_shop_headcount_demand(self.input_data_xls)

    def load_employees(self):
        self.employee_data = EmployeeData(self.input_data_xls)
        self.employee_data.create_employee_data()
        self.employee_data.create_requests(ShopData)

    @classmethod
    def shift_mapping(cls, input_str):
        # return integer
        if type(input_str) is int:
            return input_str
        elif type(input_str) is str:
            pass
        else:
            raise TypeError(f'Unrecognised type {type(input_str)}')
        input_str = input_str.lower()

        for shift_id in range(len(cls.shifts)):
            if input_str == cls.shift_full_name[shift_id].lower() or input_str == cls.shifts[shift_id]:
                return shift_id
        raise NameError(f'Unrecognised shift name pattern {input_str}')

if __name__ == '__main__':
    import pdb; pdb.set_trace()
    print('')

