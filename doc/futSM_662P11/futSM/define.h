#pragma once
#include <stdio.h>
#include <vector>
#include <string>
#include <wtypes.h>
#include <conio.h>
#include <iostream>
#include <locale>
#include <string>
#include <fstream>
#include <conio.h>
#include <time.h>
#include <sstream>
#include <locale.h>
#include <vector>
#include <map>

using namespace std;

extern FILE *logfile;
#define LOG(format, ...) fprintf(logfile, format, __VA_ARGS__); printf(format, __VA_ARGS__); fflush(logfile);

string getConfig(string title, string cfgName);

