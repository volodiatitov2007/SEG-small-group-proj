# Group Allocation system by Team *enter team name here*
A group allocation system developed for the Small Group Project assignment of the Software Engineering Group Project module at King's College London.

## Team members
The members of the team are:
- *enter full name 1 here*
- *enter full name 2 here*
- *enter full name 3 here*
- *enter full name 4 here*
- *enter full name 5 here*

## Deployment

The system has been deployed at [*insert url here*](*url*)


## Getting started

```
python3.12 -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed             # Adds sample users
python manage.py runserver
```

Then open <http://127.0.0.1:8000/> and log in as `janedoe` (a superuser) or
`johndoe` (a normal user). Both have the password `Allocation123`.

Run `python manage.py unseed` to delete all users again.

## Tests

Run all tests with `python manage.py test`. You can also run a part of them,
for example `python manage.py test allocations.tests.views`. 

[Coverage.py](https://coverage.readthedocs.io/) measures which parts of the
code the tests run. Its settings are in `.coveragerc`.

```
coverage run manage.py test       # Run the tests while measuring coverage
coverage report                   # Show the coverage of each file
coverage html                     # Write a detailed report to htmlcov/
```

Open `htmlcov/index.html` in a browser to see exactly which lines and
branches are not tested. The report leaves out code that is not ours or that
is not worth testing, such as the virtual environment, migrations, settings
and the tests themselves.