FROM python:3.6-alpine

WORKDIR /src
COPY aioqueue ./aioqueue
COPY requirements.txt setup.py ./
RUN pip install wheel \
    && python setup.py bdist_wheel \
    && pip install dist/*.whl \
    && rm -rf aioqueue

COPY examples /src/examples
