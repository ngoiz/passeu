import os
import unittest
import passeu.utils.datastructures as datastructures


class TestInterface(unittest.TestCase):
    DIRECTORY = os.path.abspath(os.path.dirname(os.path.realpath(__file__)) + '/')
    print('Current Directory ', DIRECTORY)

    input_file_xls = DIRECTORY + '/interface/input_data.xls'

    def test_employee_data_structure(self):

        shop_data = datastructures.ShopData()

        employee_data = datastructures.EmployeeData(self.input_file_xls)
        employee_data.create_employee_data()

        employee_data.create_requests(shop_data)

        print(employee_data.employees)
        print(employee_data.requests)

    def test_shop_data_structure(self):

        shop_data = datastructures.ShopData(input_data_xls=self.input_file_xls)

        shop_data.load_weekly_headcount_demand()

        print(shop_data.weekly_cover_demands)


if __name__ == '__main__':
    unittest.main()
