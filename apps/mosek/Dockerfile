# syntax=docker/dockerfile:1.4

# https://www.mosek.com/downloads/ https://www.mosek.com/downloads/list/10/ https://www.mosek.com/downloads/list/11/
ARG MAJOR_VERSION=11.0
ARG MINOR_VERSION=21

FROM debian:12-slim
LABEL maintainers="dmclf <19852218+dmclf@users.noreply.github.com>"
LABEL description="unofficial mosek docker image"

ARG MAJOR_VERSION
ARG MINOR_VERSION
ARG MOSEK_VERSION="${MAJOR_VERSION}.${MINOR_VERSION}"

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y wget bzip2 net-tools

WORKDIR /tmp
RUN --mount=type=cache,target=/tmp case `uname -m` in  aarch64) wget https://download.mosek.com/stable/${MOSEK_VERSION}/mosektoolslinuxaarch64.tar.bz2 && tar -jxvf mosektoolslinuxaarch64.tar.bz2;; x86_64) wget https://download.mosek.com/stable/${MOSEK_VERSION}/mosektoolslinux64x86.tar.bz2 && tar -jxvf mosektoolslinux64x86.tar.bz2 ;; *) echo not configured for this architecture;exit 1;; esac ; mv mosek /opt ; \
   case `uname -m` in  aarch64) ln -s /opt/mosek/${MOSEK_MAJOR_VERSION}/tools/platform/linuxaarch64 /opt/mosek/${MOSEK_MAJOR_VERSION}/tools/platform/linux;; \
   x86_64) ln -s /lib/x86_64-linux-gnu/ld-linux-x86-64.so.2 /lib64/ld-lsb-x86-64.so.3 ;ln -s /opt/mosek/${MOSEK_MAJOR_VERSION}/tools/platform/linux64x86 /opt/mosek/${MOSEK_MAJOR_VERSION}/tools/platform/linux;; \
   *) echo not configured for this architecture;exit 1;; esac; \
   useradd mosek
WORKDIR /opt

USER mosek
ENV PATH=/opt/mosek/${MOSEK_MAJOR_VERSION}/tools/platform/linux/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENTRYPOINT ["lmgrd","-z"]
CMD ["$@"]

#https://docs.mosek.com/generic/fnp_LicAdmin.pdf
#-z Runs in foreground. The default behavior is to run in the background. 
