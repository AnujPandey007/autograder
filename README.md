# C AutoGrader

To run -  
python -m pip install -r requirements.txt
python app.py


## Files

```text
autograder-simple/
├── app.py                         # Gradio interface
├── grader.py                      # Coordinator
├── rules.py                       # Read instructor rules and tests
├── feedback.py                    # Feedback and optional AI explanation
├── analyzers/
│   ├── syntax.py
│   └── correctness.py
├── runtime/
│   └── local_runner.py            # Compile and run locally
├── examples/
│   ├── question1/
│   │   ├── instructor.json        # Addition rules
│   │   ├── student1.c             # Correct addition
│   │   └── student2.c             # Incorrect subtraction
│   └── question2/
│       ├── instructor.json        # Multiplication rules
│       └── student1.c             # Correct multiplication
├── tests/
│   ├── add/
│   │   └── tests.json             # Addition input/expected output pairs
│   └── mul/
│       └── tests.json             # Multiplication input/expected output pairs
```