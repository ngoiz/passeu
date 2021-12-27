def negated_bounded_span(works, start, length):
    """Filters an isolated sub-sequence of variables assined to True.

  Extract the span of Boolean variables [start, start + length), negate them,
  and if there is variables to the left/right of this span, surround the span by
  them in non negated form.

  Args:
    works: a list of variables to extract the span from.
    start: the start to the span.
    length: the length of the span.

  Returns:
    a list of variables which conjunction will be false if the sub-list is
    assigned to True, and correctly bounded by variables assigned to False,
    or by the start or end of works.
  """
    sequence = []
    # Left border (start of works, or works[start - 1])
    if start > 0:
        sequence.append(works[start - 1])
    for i in range(length):
        sequence.append(works[start + i].Not())
    # Right border (end of works or works[start + length])
    if start + length < len(works):
        sequence.append(works[start + length])
    return sequence


def add_soft_sequence_constraint(model, works, hard_min, soft_min, min_cost,
                                 soft_max, hard_max, max_cost, prefix):
    """Sequence constraint on true variables with soft and hard bounds.

  This constraint look at every maximal contiguous sequence of variables
  assigned to true. If forbids sequence of length < hard_min or > hard_max.
  Then it creates penalty terms if the length is < soft_min or > soft_max.

  Args:
    model: the sequence constraint is built on this model.
    works: a list of Boolean variables.
    hard_min: any sequence of true variables must have a length of at least
      hard_min.
    soft_min: any sequence should have a length of at least soft_min, or a
      linear penalty on the delta will be added to the objective.
    min_cost: the coefficient of the linear penalty if the length is less than
      soft_min.
    soft_max: any sequence should have a length of at most soft_max, or a linear
      penalty on the delta will be added to the objective.
    hard_max: any sequence of true variables must have a length of at most
      hard_max.
    max_cost: the coefficient of the linear penalty if the length is more than
      soft_max.
    prefix: a base name for penalty literals.

  Returns:
    a tuple (variables_list, coefficient_list) containing the different
    penalties created by the sequence constraint.
  """
    cost_literals = []
    cost_coefficients = []

    # Forbid sequences that are too short.
    for length in range(1, hard_min):
        for start in range(len(works) - length + 1):
            model.AddBoolOr(negated_bounded_span(works, start, length))

    # Penalize sequences that are below the soft limit.
    if min_cost > 0:
        for length in range(hard_min, soft_min):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = ': under_span(start=%i, length=%i)' % (start, length)
                lit = model.NewBoolVar(prefix + name)
                span.append(lit)
                model.AddBoolOr(span)
                cost_literals.append(lit)
                # We filter exactly the sequence with a short length.
                # The penalty is proportional to the delta with soft_min.
                cost_coefficients.append(min_cost * (soft_min - length))

    # Penalize sequences that are above the soft limit.
    if max_cost > 0:
        for length in range(soft_max + 1, hard_max + 1):
            for start in range(len(works) - length + 1):
                span = negated_bounded_span(works, start, length)
                name = ': over_span(start=%i, length=%i)' % (start, length)
                lit = model.NewBoolVar(prefix + name)
                span.append(lit)
                model.AddBoolOr(span)
                cost_literals.append(lit)
                # Cost paid is max_cost * excess length.
                cost_coefficients.append(max_cost * (length - soft_max))

    # Just forbid any sequence of true variables with length hard_max + 1
    for start in range(len(works) - hard_max):
        model.AddBoolOr(
            [works[i].Not() for i in range(start, start + hard_max + 1)])
    return cost_literals, cost_coefficients


def add_soft_sum_constraint(model, works, hard_min, soft_min, min_cost,
                            soft_max, hard_max, max_cost, prefix):
    """Sum constraint with soft and hard bounds.

  This constraint counts the variables assigned to true from works.
  If forbids sum < hard_min or > hard_max.
  Then it creates penalty terms if the sum is < soft_min or > soft_max.

  Args:
    model: the sequence constraint is built on this model.
    works: a list of Boolean variables.
    hard_min: any sequence of true variables must have a sum of at least
      hard_min.
    soft_min: any sequence should have a sum of at least soft_min, or a linear
      penalty on the delta will be added to the objective.
    min_cost: the coefficient of the linear penalty if the sum is less than
      soft_min.
    soft_max: any sequence should have a sum of at most soft_max, or a linear
      penalty on the delta will be added to the objective.
    hard_max: any sequence of true variables must have a sum of at most
      hard_max.
    max_cost: the coefficient of the linear penalty if the sum is more than
      soft_max.
    prefix: a base name for penalty variables.

  Returns:
    a tuple (variables_list, coefficient_list) containing the different
    penalties created by the sequence constraint.
  """
    cost_variables = []
    cost_coefficients = []
    sum_var = model.NewIntVar(hard_min, hard_max, '')
    # This adds the hard constraints on the sum.
    model.Add(sum_var == sum(works))

    # Penalize sums below the soft_min target.
    if soft_min > hard_min and min_cost > 0:
        delta = model.NewIntVar(-len(works), len(works), '')
        model.Add(delta == soft_min - sum_var)
        # TODO(user): Compare efficiency with only excess >= soft_min - sum_var.
        excess = model.NewIntVar(0, 7, prefix + ': under_sum')
        model.AddMaxEquality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(min_cost)

    # Penalize sums above the soft_max target.
    if soft_max < hard_max and max_cost > 0:
        delta = model.NewIntVar(-7, 7, '')
        model.Add(delta == sum_var - soft_max)
        excess = model.NewIntVar(0, 7, prefix + ': over_sum')
        model.AddMaxEquality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(max_cost)

    return cost_variables, cost_coefficients


def add_soft_sum_int_constraint(model, work_hours, hard_min, soft_min, min_cost,
                                soft_max, hard_max, max_cost, prefix):
    """
    Enforces the sum of list of integer variables to be within hard_min and hard_max, and imposes
    a linear penalty when the sum below soft_min or above soft_max. The penalty is linear, being
    bounded between min_cost and 0 if under the soft_min or between 0 and max_cost if above soft_max

    Args:
        model (cp_model.CpModel):
        work_hours (list(IntegerVariables)): List of IntegerVariables
        hard_min (int): Hard minimum
        soft_min (int): Soft minimum
        min_cost (int): Maximum cost to apply if sum is hard_min
        soft_max (int): Soft maximum
        hard_max (int): Hard maximum
        max_cost (int): Maximum cost to apply if sum is hard_max
        prefix (str): String prefix for variable name

    Returns:
        tuple: (variables, coefficients) to be added to model minimisation function
    """

    cost_variables = []
    cost_coefficients = []
    sum_var = model.NewIntVar(hard_min, hard_max, prefix)
    # This adds the hard constraints on the sum.
    model.Add(sum_var == sum(work_hours))

    if soft_min > hard_min and min_cost > 0: # else nothing to penalise

        # delta = soft_min - sum_var, where sum_var in [hard_min, hard_max]
        # therefore, delta must satisfy the following ranges
        delta = model.NewIntVar(soft_min - hard_max, soft_min - hard_min, '')
        model.Add(delta == soft_min - sum_var)

        # if delta < 0, the variable is above soft_min -> no penalty
        # therefore excess (which is the penalty applied) is [0, max(delta)]
        excess = model.NewIntVar(0, soft_min - hard_min, prefix + ': under_sum')
        model.AddMaxEquality(excess, [delta, 0])  # if delta < 0, then the variable is above soft_min and no need for penalty
        cost_variables.append(excess)
        cost_coefficients.append(min_cost)

    if soft_max < hard_max and max_cost > 0:
        delta = model.NewIntVar(hard_min - soft_max, hard_max - soft_max, '')
        model.Add(delta == sum_var - soft_max)

        # if delta < 0, then sum_var < soft_max -> no need por penalty
        excess = model.NewIntVar(0, hard_max - soft_max, prefix + ': over_sum')
        model.AddMaxEquality(excess, [delta, 0])
        cost_variables.append(excess)
        cost_coefficients.append(max_cost)

    return cost_variables, cost_coefficients

# IDEA!
# Add constraints as classes, which have methods to add the constraint to a model
# Also that they have the postprocessing method to write the result given a model of that
# constraint


class Constraint:

    def __init__(self, shop_data):
        self.shop_data = shop_data  # passeu.utils.datastructures.ShopData

    def apply(self, model, work, **kwargs):
        pass

    def output(self):
        pass


class WorkerExperienceDay(Constraint):

    def apply(self, model, work, **kwargs):
        """
        Adds a hard constraint that for each day, across all shifts there must be enough workers of a given
        level

        Args:
            model (cp_model.CpModel()):
            work (dict): Dictionary of (employee, shift, day): BooleanVar

        Keyword Args:
            daily_experience_demands (list(tuple)): List of n_days, where each entry is a tuple of required employees
              per level

        """
        daily_experience_demands = kwargs.get('daily_experience_demands', None)  # maybe add as property via set attr
        obj_variables = []
        obj_coefficients = []

        num_days = self.shop_data.num_days
        employees = self.shop_data.employee_data.employees
        num_employees = self.shop_data.employee_data.num_employees
        levels = self.shop_data.employee_data.levels

        for d in range(num_days):
            for l in levels:
                variables = []
                for e in range(num_employees):
                    if employees[e].level == l:
                        variables.extend([work[(e, s, d)] for s in range(1, self.shop_data.num_shifts)])
                prefix = f'daily_experience(day={d}, level={l})'
                obj_vars, obj_coeffs = add_soft_sum_int_constraint(model, variables,
                                                                   hard_min=daily_experience_demands[d][l],
                                                                   soft_min=daily_experience_demands[d][l],
                                                                   min_cost=0,
                                                                   soft_max=daily_experience_demands[d][l],
                                                                   hard_max=daily_experience_demands[d][l]+3,
                                                                   max_cost=5,
                                                                   prefix=prefix)
                obj_variables.extend(obj_vars)
                obj_coefficients.extend(obj_coeffs)
        return obj_variables, obj_coefficients


class WorkerExperienceShift(Constraint):
    def apply(self, model, work, **kwargs):
        """

        Args:
            model:
            work:
            **kwargs:

        Returns:

        """
        obj_variables = []
        obj_coefficients = []

        daily_shift_experience_demands = kwargs.get('daily_shift_experience_demands', None)  # maybe add as property via set attr

        num_days = self.shop_data.num_days
        employees = self.shop_data.employee_data.employees
        num_employees = self.shop_data.employee_data.num_employees
        levels = self.shop_data.employee_data.levels

        for d in range(num_days):
            for s in range(1, self.shop_data.num_shifts):
                for l in levels:
                    variables = []
                    for e in range(num_employees):
                        if employees[e].level == l:
                            variables.append(work[(e, s, d)])
                    prefix = f'experience_l{l}d{d}{s}'
                    obj_vars, obj_coeffs = add_soft_sum_int_constraint(model, variables,
                                                                       hard_min=daily_shift_experience_demands[d][s][l],
                                                                       soft_min=daily_shift_experience_demands[d][s][l],
                                                                       min_cost=5,
                                                                       soft_max=100,
                                                                       hard_max=100,
                                                                       max_cost=0,
                                                                       prefix=prefix)
                    obj_variables.extend(obj_vars)
                    obj_coefficients.extend(obj_coeffs)

        return obj_variables, obj_coefficients


class ContractHours(Constraint):

    def apply(self, model, work_hours, **kwargs):
        """
        Enforce maximum number of working hours

        Args:
            model (cp_model.CpModel):
            work_hours (dict): Dictionary of (employee, day): IntegerVar containing working hours per day

        Returns:

        """
        num_employees = self.shop_data.employee_data.num_employees
        employees = self.shop_data.employee_data.employees

        # Max weekly working hours - currently a hard constraint to meet contract hours
        for e in range(num_employees):
            model.Add(sum([work_hours[(e, d)] for d in range(self.shop_data.num_days)]) == employees[e].contract_weekly_hours)


class OvertimeContractHours(Constraint):

    def apply(self, model, work_hours, **kwargs):
        """
        Applies a linear penalty constraint on workers doing overtime (if allowed).

        For each week, worker worked hours shall be above contract_hours but under contract_hours + max_overtime.
        A linear penalty is applied on the number of overtime hours

        Args:
            model (cp_model.CpModel): model
            work_hours (dict): Dictionary of (employee, day): IntegerVar containing employee working hours per day

        Keyword Args:
             overtime_max_cost (int): Maximum penalty applied for maximum overtime

        Returns:
            tuple: (variables, coefficients) overtime variables and excess coefficients to be added to model
              minimisation function.

        """
        overtime_max_cost = kwargs.get('overtime_max_cost', 5)
        cost_variables = []
        cost_coefficients = []

        num_employees = self.shop_data.employee_data.num_employees
        employees = self.shop_data.employee_data.employees

        for e in range(num_employees):
            prefix = f'worker{e}_weeklyhours'
            contract_hours = employees[e].contract_weekly_hours
            max_overtime = employees[e].maximum_overtime

            sum_work_hours_week = [work_hours[(e, d)] for d in range(self.shop_data.num_days)]

            variables, coefficients = add_soft_sum_int_constraint(model,
                                                                     sum_work_hours_week,
                                                                     contract_hours,
                                                                     contract_hours,
                                                                     0,
                                                                     contract_hours,
                                                                     contract_hours + max_overtime,
                                                                     overtime_max_cost,
                                                                     prefix)

            cost_variables.extend(variables)
            cost_coefficients.extend(coefficients)

        return cost_variables, cost_coefficients


# class DailyManhoursDemand(Constraint):
#
#     def apply(self, model, work_hours, **kwargs):
