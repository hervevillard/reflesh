# Dockerfile, Image, Container
FROM python:3.12.2 
# files to use, dot here inform Docker that it is in the current folder
ADD main.py . 
#dependencies to install 
RUN pip install requests bs4 playwright
RUN playwright install --with-deps chromium
# executable
CMD ["python", "./main.py"]
