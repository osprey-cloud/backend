# use an official python runtime as the base image
# FROM python:3.6
FROM python:3.10

# set the (container) working directory
WORKDIR /app

COPY requirements.txt /app/requirements.txt

# install dependencies
RUN pip install -r requirements.txt

# copy current (local) directory contents into the container
COPY . /app

# make port available to the world outside this container
EXPOSE 5000

# run when the container launches
CMD ["/app/scripts/start.sh"]