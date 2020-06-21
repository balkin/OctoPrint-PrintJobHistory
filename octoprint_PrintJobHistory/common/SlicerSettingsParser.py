# coding=utf-8
from __future__ import absolute_import

import logging
import os

MAX_GCODE_LINES_BEFORE_STOP_READING = 10
LINE_RESULT_GCODE = "LR:gcode"
LINE_RESULT_SETTINGS = "LR:settings"
LINE_RESULT_OTHERS = "LR:others"

# Model of Slicer Settings
class SlicerSettings(object):

	def __init__(self):
		self.settingsAsText = ""
		self.settingsAsDict = dict()

	def isKeyAlreadyExtracted(self, key):
		return key in self.settingsAsDict

	def addKeyValueSetting(self, key, value):
		self.settingsAsDict.update({key:value})

	def addKeyValueSettingsAsText(self, settingsText):
		self.settingsAsText += settingsText

###########################################################
# Parse reads all 'key = values' out of the gcode file
# - It reads to top and the bottom
# - It reads till a block of gcode-commands will be detected
# - No overlappig between the top-block and the bottom-block
class SlicerSettingsParser(object):

	def __init__(self, parentLogger):
		self._logger = logging.getLogger(parentLogger.name + "." + self.__class__.__name__)
		# self._logger.setLevel(logging.DEBUG)

	def extractSlicerSettings(self, gcodeFilePath, includedSettingsKeyList):

		self._logger.info("Start parsing Slicer-Settings")
		# Read the file from top
		# Read the file from bottom
		# read key-value

		# - Make sure that the top-region is not overlappig with bottom region
		# - Stop reading after you read a definied amount of gcode continusly (no interruption -> gcode-block)
		slicerSettings = SlicerSettings()

		lastLineResult = None # type of line
		gcodeCount = 0
		readingOrder = 0 # 0=forward; 1=reverse 2++=finished
		reverseReadinStarted = False
		lastTopFilePosition = 0	# needed for overlapping detection of top-region and bottom-region
		lineNumber = 0
		with open(gcodeFilePath, 'r') as fileHandle:
			while True:

				if (readingOrder == 0):
					# Forward reading
					line = fileHandle.readline()
					lastTopFilePosition = fileHandle.tell()
					lineNumber += 1
					pass
				else:
					# Reverse reading
					# Jump to the end
					if (reverseReadinStarted == False):
						fileHandle.seek(0, os.SEEK_END)
						reverseReadinStarted = True
						lineNumber = 0
						gcodeCount = 0
					line = self.nextReversedLine(fileHandle, lastTopFilePosition)
					lineNumber += 1

				if (line == ''):
					# EOF reached
					readingOrder += 1

					if (readingOrder == 1):
						lineNumber = 0
						continue
					else:
						# finaly top/Bottom reading is done
						break

				lineResult = self.processLine(line, slicerSettings)
				# print(lineResult)
				if (lineResult == LINE_RESULT_GCODE):
					gcodeCount += 1
					if (lastLineResult == LINE_RESULT_GCODE):
						if (gcodeCount >= MAX_GCODE_LINES_BEFORE_STOP_READING):
							# forward reading finished, switch to reverse
							if (reverseReadinStarted == True):
								# finaly top/Bottom reading is done
								break
							readingOrder += 1
							continue
				else:
					gcodeCount = 0
				lastLineResult = lineResult

				debugInformation = "ORDER: " + str(readingOrder) + " LineNumber: " + str(lineNumber) + " GCodeFound: " + str(gcodeCount)
				# print(debugInformation)
				# self._logger.debug(debugInformation)

				pass
		self._logger.debug(" Slicer-Settings:")
		self._logger.debug(slicerSettings.settingsAsDict)
		self._logger.info("Finished parsing Slicer-Settings")
		return slicerSettings


	# Process a Single-Line
	def processLine(self, line, slicerSettings):
		# print(line)
		if (line == None or line == '' ):
			# EMPTY
			return LINE_RESULT_OTHERS

		line = line.lstrip()
		if (len(line) == 0):
			# EMPTY
			return LINE_RESULT_OTHERS

		if (line[0] == ";"):
			# special comments
			if ("enerated" in line):
				key = "generated by"
				value = line[1:]
				slicerSettings.addKeyValueSetting(key, value)
				slicerSettings.addKeyValueSettingsAsText(line)
				return LINE_RESULT_SETTINGS
			# Cura put JSON fragments to SETTINGS2_ comments -> ignore it
			if (";SETTING_" in line):
				return LINE_RESULT_OTHERS

			# KeyValue extraction
			if ('=' in line):
				keyValue = line.split('=', 1) # 1 == only the first =
				key = keyValue[0].strip()
				value = keyValue[1].strip()
				if (slicerSettings.isKeyAlreadyExtracted(key) == False):
					slicerSettings.addKeyValueSetting(key, value)
					slicerSettings.addKeyValueSettingsAsText(line)
				return LINE_RESULT_SETTINGS

			return LINE_RESULT_OTHERS

		# Must be a gcode
		return LINE_RESULT_GCODE

	def nextReversedLine(self, fileHandle, lastTopFilePosition):
		line = ''

		filePosition = fileHandle.tell()
		if (filePosition <=0):
			return line
		if (filePosition <= lastTopFilePosition):
			self._logger.debug("We reached the already parsed top-region during reverse-parsing")
			print("We reached the already parsed top-region during reverse-parsing")
			return line

		while filePosition >= 0:
			fileHandle.seek(filePosition)
			current_char = fileHandle.read(1)
			line += current_char

			if (filePosition == 0):
				line = line[::-1]
				fileHandle.seek(0)
				break

			fileHandle.seek(filePosition - 1)
			next_char = fileHandle.read(1)
			if next_char == "\n":
				line = line[::-1]
				# HACK
				if len(line)==0:
					line = " "
				fileHandle.seek(filePosition - 1)
				break
			filePosition -= 1

		return line




if __name__ == '__main__':
	parsingFilename = "/Users/o0632/0_Projekte/3DDruck/OctoPrint/OctoPrint-PrintJobHistory/testdata/slicer-settings/CURA_schieberdeckel2.gcode"
	#parsingFilename = "/Users/o0632/0_Projekte/3DDruck/OctoPrint/OctoPrint-PrintJobHistory/testdata/slicer-settings/simple.gcode"


	testLogger = logging.getLogger("testLogger")
	settingsParser = SlicerSettingsParser(testLogger)
	slicerSettings = settingsParser.extractSlicerSettings(parsingFilename, None)

	print("TEXT: "+slicerSettings.settingsAsText)
	print(slicerSettings.settingsAsDict)
	print("done")
