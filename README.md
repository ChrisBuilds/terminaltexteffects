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

### Your own coverage tool

Mihail-Dimosthenis Cretu

Function 1 : xterm_to_hex
Link:<https://github.com/cretud/terminaltexteffects/commit/9e3b9c2da09ec9539e140c4daefb37084e6c3d5d>
Screenshot:[Personal Branch Coverage Tool](README\CoverageToolDimos.png)

Function 2 : is_valid_color
Link:<https://github.com/cretud/terminaltexteffects/commit/9e3b9c2da09ec9539e140c4daefb37084e6c3d5d>
Screenshot:[Personal Branch Coverage Tool](README\CoverageToolDimos.png)

Function 3 : type_parser
Link:<https://github.com/cretud/terminaltexteffects/commit/9e3b9c2da09ec9539e140c4daefb37084e6c3d5d>
Screenshot:[Personal Branch Coverage Tool](README\CoverageToolDimos.png)

<The following is supposed to be repeated for each group member>

<Group member name>

<Function 1 name>

<Show a patch (diff) or a link to a commit made in your forked repository that shows the instrumented code to gather coverage measurements>

<Provide a screenshot of the coverage results output by the instrumentation>

<Function 2 name>

<Provide the same kind of information provided for Function 1>

## Coverage improvement

### Individual tests

Mihail-Dimosthenis Cretu

Test 1:test_type_parser_valid + Test 2:test_type_parser_invalid
Link:<>
Screenshot Before:[Personal Branch Coverage Tool](README\type_parserFloatBefore.png)
Screenshot After:[Personal Branch Coverage Tool](README\type_parserFloat.png)

The coverage has improved from 0% to 100%. First test checks the first branch of the method when input is valid and the second one checks the second branch when the input is invalid.

Test 3:test_xterm_to_hex_valid + Test 4:test_xterm_to_hex_invalid
Link:<>
Screenshot Before:[Personal Branch Coverage Tool](README\hextermBefore.png)
Screenshot After:[Personal Branch Coverage Tool](README\hexterm.png)

The coverage has improved from 0% to 100%. First test checks the first branch of the method when input is valid and the second one checks the second branch when the input is invalid.

Test 5:test_is_valid_color_invalid_length +
Test 6:test_is_valid_color_invalid_characters +
Test 7:test_is_valid_color_number 
Link:<>
Screenshot Before:[Personal Branch Coverage Tool](README\hextermBefore.png)
Screenshot After:[Personal Branch Coverage Tool](README\hexterm.png)

The coverage has improved from 56% to 100%. First test checks the branch of the method when input is invalid by having the wrong string length, the second one checks the branch of the method when input is invalid by having invalid characters in the string, and the last one check if the method return true or false if the based on the value of the integer, outside the range 1-256 false inside true.

<The following is supposed to be repeated for each group member>

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

