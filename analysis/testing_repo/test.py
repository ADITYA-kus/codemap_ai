import pandas as pd
import numpy as np 
def introduction1():
    print("helow Aditya ")

class Student1:
    def __init__(self):
        name=''
        roll=''
        branch=''
        self.info1()
      
    def info1(self):
        self.name="aditya"
        self.roll="240"
        self.branch="ece"
        self.display()

    def display1(self):
        print("name is: ",self.name)
        print("roll is:",self.roll)
        print("branch is:",self.branch)




Student1()



import os


from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


"""Module docstring: demo repo for CodeMap."""

def introduction():
    """Prints an intro message."""
    print("Hello")

class Student:
    """Represents a student."""

    def info(self):
        """Calls display() to show student details."""
        self.display()

    def display(self):
        """Prints student details."""
        print("...")


def demo(a: int, b=10, *, c="x", **kw) -> str:
    return str(a + b)


def r1():
    return

def r2():
    return None

def r3():
    return 5

def r4():
    x = 10
    return x

def r5(a, b):
    return a + b

def r6():
    return str(123)

