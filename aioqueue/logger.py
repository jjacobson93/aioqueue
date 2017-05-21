import logging

logger = logging.getLogger('aioqueue')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())