#!/bin/bash

#This script takes a query name as input.
#It then loads the file queries.pl and sets the input query as a goal.
#The output should be results that satisfied the query passed in.
#The input query should be one that has been defined in queries.pl

swipl --quiet -t "ignore($1),halt(1)" --consult-file queries.pl
