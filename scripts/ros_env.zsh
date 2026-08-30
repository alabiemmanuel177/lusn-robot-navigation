#!/usr/bin/env zsh

if [[ ! -f /opt/ros/jazzy/setup.zsh ]]; then
  print -u2 "ROS 2 Jazzy is not installed at /opt/ros/jazzy"
  return 1
fi

source /opt/ros/jazzy/setup.zsh
typeset _language_nav_env_file="${${(%):-%N}:A}"
typeset -g LANGUAGE_NAV_ROOT="${_language_nav_env_file:h:h}"
unset _language_nav_env_file
export PYTHONPATH="${LANGUAGE_NAV_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export ROS_LOG_DIR="${LANGUAGE_NAV_ROOT}/ros_ws/log/ros"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://${LANGUAGE_NAV_ROOT}/configs/dds/cyclonedds.xml"
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_IP=127.0.0.1
export GZ_PARTITION=language_nav
export PYTHONHASHSEED=0

if [[ -f "${LANGUAGE_NAV_ROOT}/ros_ws/install/local_setup.zsh" ]]; then
  source "${LANGUAGE_NAV_ROOT}/ros_ws/install/local_setup.zsh"
fi
