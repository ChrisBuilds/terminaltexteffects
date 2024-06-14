# Report for Assignment 1

## Project chosen

Name: Terminal Text Effects

URL: [Terminal Text Effects](https://github.com/ChrisBuilds/terminaltexteffects.git)

Number of lines of code and the tool used to count it: 12482 found by Lizard

Programming language: Python

## Coverage measurement

### Existing tool

The tool that we used was Coverage.py
After we cloned the repository we opened the powershell.
We runned the command "coverage run -m pytest tests/"
And then we run "coverage report" to get the following report:

[Coverage Results](README\BeforeTestCoverage.png)

## Coverage improvement

### Individual tests

<The following is supposed to be repeated for each group member>

Mihail-Dimosthenis Cretu

test_type_parser_valid and test_type_parser_invalid

<Show a patch (diff) or a link to a commit made in your forked repository that shows the new/enhanced test>

[1stMethod](README\Dimos1.png)

To enhance the coverage for the PositiveFloat.type_parser method from 0% to 100%, I developed a test suite. This suite validates that the method correctly parses positive float values and appropriately raises an error for invalid inputs. Prior to these tests, the method had no coverage; thus, this suite significantly improved its coverage.

test_is_valid_color_invalid_characters, test_is_valid_color_too_long, test_is_valid_color_not_string

<Show a patch (diff) or a link to a commit made in your forked repository that shows the new/enhanced test>

[1stMethod](README\Dimos2.png)

To enhance the coverage for the is_valid_color method from 56% to 100%, I developed a test suite. This suite validates that the method correctly return false values and can also operate with integers between the value of 1 and 256.

<Group member name>

<Test 1>

<Show a patch (diff) or a link to a commit made in your forked repository that shows the new/enhanced test>

<Provide a screenshot of the old coverage results (the same as you already showed above)>

<Provide a screenshot of the new coverage results>

<State the coverage improvement with a number and elaborate on why the coverage is improved>

<Test 2>

<Provide the same kind of information provided for Test 1>

### Overall

<Provide a screenshot of the old coverage results by running an existing tool (the same as you already showed above)>

<Provide a screenshot of the new coverage results by running the existing tool using all test modifications made by the group>

## Statement of individual contributions

<Write what each group member did>
