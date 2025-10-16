import logging.handlers
from logging import handlers
import unittest
import os

temp = os.path.dirname(__file__)
os.chdir(temp + '//log')

# Log formatter 생성
formatter = logging.Formatter('[%(levelname)s] %(asctime)s (%(filename)s:%(lineno)d) > %(message)s')

# Logger 객체 생성 및 Log Level 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# File Handler 생성
fileLogHandler = handlers.TimedRotatingFileHandler(filename='vpes.log', when='midnight', interval=1, encoding='utf-8')
fileLogHandler.setLevel(logging.DEBUG)

# Stream Handler 생성
streamLogHandler = logging.StreamHandler()
streamLogHandler.setLevel(logging.INFO)

# Logger 객체에 formatter 설정
streamLogHandler.setFormatter(formatter)
fileLogHandler.setFormatter(formatter)
fileLogHandler.suffix = "%Y%m%d"

# Logger 객체에 Handler 설정
logger.addHandler(streamLogHandler)
# logger.addHandler(fileLogHandler)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)


