#!/bin/bash

read -p "Commit Message: " input

git add .
git commit -m "$input"
git push

