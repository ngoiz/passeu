import pandas as pd


def create_employee_data(input_file_xls):
    """

    Args:
        input_file_xls (str): Path to excel file containing input data

    Returns:
        tuple: list(dict): list of {name:Name, contract_weekly_hours:Hours} and lookup dictionary employee_name:employee_id
    """
    df = pd.read_excel(input_file_xls, sheet_name='Employees', header=0)
    employees = []
    employee_lookup = {}

    for index, row in df.iterrows():
        employee = {'name': row['Name'], 'contract_weekly_hours': int(row['Hours'])}
        employees.append(employee)
        employee_lookup[row['Name']] = index

    return employees, employee_lookup


def create_request_list(input_file_xls):
    df = pd.read_excel(input_file_xls, sheet_name='Requests', header=0)
    requests = []
    for index, row in df.iterrows():
        requests.append((row['Name'], row['Shift'], int(row['Day']), int(row['Weight'])))

    return requests


def create_shop_headcount_demand(input_file_xls):
    df = pd.read_excel(input_file_xls, sheet_name='ShopDemands', header=0)
    headcount_demand = []
    order = []
    for index, row in df.iterrows():
        order.append(row['Day'])
        headcount_demand.append((int(row['Morning']), int(row['Afternoon']), int(row['Close'])))

    return [headcount_demand[i_order] for i_order in order]
