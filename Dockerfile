FROM rocker/shiny:latest

RUN R -e "install.packages(c( \
    'shiny', \
    'shinydashboard', \
    'plotly', \
    'DT', \
    'dplyr', \
    'readr', \
    'stringr', \
    'igraph', \
    'visNetwork', \
    'lubridate' \
), repos='https://cloud.r-project.org')"

COPY . /srv/shiny-server/

EXPOSE 3838

CMD ["/usr/bin/shiny-server"]