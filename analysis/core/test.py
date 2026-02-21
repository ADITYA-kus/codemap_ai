import pandas as pd
import numpy as np 
def introduction():
    print("helow Aditya ")

class Student:
    def __init__(self):
        name=''
        roll=''
        branch=''
        self.info()
      
    def info(self):
        self.name="aditya"
        self.roll="240"
        self.branch="ece"
        self.display()

    def display(self):
        print("name is: ",self.name)
        print("roll is:",self.roll)
        print("branch is:",self.branch)




Student()



import os


from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
