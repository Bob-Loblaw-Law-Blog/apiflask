#!/bin/zsh
autoload colors; colors
echo $fg[green]Starting project initialisation$reset_color
echo $fg[cyan]First step: virtual environment$reset_color
virtualenv venv
source venv/bin/activate
echo $fg[yellow]Second step: install core requirements$reset_color
pip install flask flask-marshmallow marshmallow webargs flask-httpauth apispec setuptools build tox
echo $fg[red]Third step: build project$reset_color
python3 -m build
