# -*- coding: utf-8 -*-
"""
Created on Wed May  8 21:29:07 2019

@author: Afei
"""
import matplotlib.image as mpimg
inputname = "examples/test2.bmp"

text = open(inputname, "rb")
data = text.read()
data2 = mpimg.imread('examples/test2.bmp') 