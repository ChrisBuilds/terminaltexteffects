import pytest
import math
from terminaltexteffects.utils.easing import in_elastic  

# Initialize coverage tracking global variable
branch_coverage = {
    "in_elastic_branch_0": False,  # branch when progress_ratio == 0
    "in_elastic_branch_1": False,  # branch when progress_ratio == 1
    "in_elastic_branch_else": False,  # branch for the else case
}

def in_elastic(progress_ratio: float) -> float:
    """ 
    Ease in using an elastic function.

    Args: 
        progress_ratio (float): the ratio of the current step to the maximum steps 

    Returns: 
        float: 0 <= n <= 1 eased value 
    """ 

    c4 = (2 * math.pi) / 3 

    if progress_ratio == 0:
        branch_coverage["in_elastic_branch_0"] = True
        return 0 
    elif progress_ratio == 1:
        branch_coverage["in_elastic_branch_1"] = True
        return 1 
    else:
        branch_coverage["in_elastic_branch_else"] = True
        return -(2 ** (10 * progress_ratio - 10)) * math.sin((progress_ratio * 10 - 10.75) * c4)

def print_coverage():
    total_branches = len(branch_coverage)
    hit_branches = sum(hit for hit in branch_coverage.values())
    coverage_percentage = (hit_branches / total_branches) * 100
    for branch, hit in branch_coverage.items():
        print(f"{branch} was {'hit' if hit else 'not hit'}")
    print(f"Coverage: {coverage_percentage:.2f}%")

def main():
    # Example
    try:
        result = in_elastic(0)
    except:
        pass

    try:
        result = in_elastic(1)
    except:
        pass

    try:
        result = in_elastic(0.5)
    except:
        pass

    try:
        result = in_elastic(0.25)
    except:
        pass

    try:
        result = in_elastic(0.75)
    except:
        pass
    print_coverage()

if __name__ == "__main__":
    main()
