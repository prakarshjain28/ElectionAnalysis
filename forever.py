#to run the twitter program ok.py

from subprocess import Popen
import sys

filename='ok.py'
while True:
	print("\n Starting "+filename)
	p=Popen("python3 "+filename,shell=True)
	p.wait()
