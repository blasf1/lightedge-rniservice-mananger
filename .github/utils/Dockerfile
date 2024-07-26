FROM ubuntu:24.04 AS lightedge-rniservice-manager

# Install requirements and dependencies
RUN buildDeps='python3-pip wget netcat-traditional' \
    && set -x \
    && apt-get update \
    && apt-get install -y $buildDeps \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install empower-core==1.0.13 --break-system-packages\
    && pip3 install tornado==6.2 --break-system-packages\
    && pip3 install construct==2.10.68 --break-system-packages\
    && pip3 install pymodm==0.4.3 --break-system-packages\
    && pip3 install python-stdnum==1.17 --break-system-packages\
    && pip3 install requests==2.28.1 --break-system-packages\
    && wget https://github.com/eficode/wait-for/releases/download/v2.2.4/wait-for -P /bin \
    && chmod +x /bin/wait-for 

COPY . /

# Create configuration soft-links
RUN rm -rf /.git /.gitignore /.github \
    && ln -sf /conf /etc/lightedge-rniservice-manager

# Add the launcher script
ADD entrypoint.sh /

# Define the entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Expose API
EXPOSE 8887
