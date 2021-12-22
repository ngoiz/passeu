import passeu.interface.interface as interface
import os
import unittest


class TestInterface(unittest.TestCase):
    DIRECTORY = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + '/')
    print('Current Directory ', DIRECTORY)

    input_file_xls = DIRECTORY + '/input_data.xls'

    def test_interface(self):
        employees, employee_lookup = interface.create_employee_data(self.input_file_xls)

        print(employees)
        print(employee_lookup)

    def test_employee_requests(self):
        requests = interface.create_request_list(self.input_file_xls)
        print(requests)


    def test_shop_headcount_demand(self):

        headcount = interface.create_shop_headcount_demand(self.input_file_xls)

        print(headcount)

if __name__ == '__main__':
    unittest.main()
