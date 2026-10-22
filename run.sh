#!/usr/bin/env bash
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_BEGIN
# *****************************************************************************
# Project   : HYDRA-UMC-LOCAL-TECHNICIAN
# Script    : run.sh
# Purpose   : Runtime workflow for the project entry point.
# Author    : JuanenRac (Electro Hobby 3D)
# Email     : electrohobby3d@gmail.com
# Copyright : (C) 2026 JuanenRac
# License   : GPL-3.0-or-later - see LICENSE
# *****************************************************************************
# HYDRA_UMC_SCRIPT_STANDARD_HEADER_END
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_BEGIN
printf '\n*******************************************************************************\n'
printf '%s\n' "* HYDRA-UMC-LOCAL-TECHNICIAN - run.sh"
printf '%s\n' "* Mode      : RUN WORKFLOW"
printf '%s\n' "* Author    : JuanenRac (Electro Hobby 3D)"
printf '%s\n' "* Email     : electrohobby3d@gmail.com"
printf '%s\n' "* Copyright : (C) 2026 JuanenRac"
printf '%s\n' "* License   : GPL-3.0-or-later - see LICENSE"
printf '%s\n' "* ------------------------------------------------------------------------- *"
printf '%s\n' "* 1. Resolve the runtime prerequisites declared by this script."
printf '%s\n' "* 2. Start the project entry point and forward user arguments unchanged."
printf '%s\n' "* 3. Preserve its result and keep an interactive terminal open."
printf '%s\n' "*******************************************************************************"
printf '\n'
# HYDRA_UMC_SCRIPT_STANDARD_BANNER_END
# Runs HYDRA-UMC-LOCAL-TECHNICIAN. Run ./build.sh first.
#
# Usage:
#   ./run.sh                                          - real demo: validates
#                                                        the shipped example
#                                                        ToolRequest fixture
#   ./run.sh contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
# This is a CLI-only delivery (no GUI, no inference) - see cli.py's own header comment.
set -uo pipefail  # no -e: we need to reach the trap below even if the process exits non-zero
cd "$(dirname "$0")"

# Keep the window open if this was double-clicked instead of run from an
# already-open terminal - real output would otherwise flash-close before
# it's readable. Only prompts when stdin is actually a terminal (never in
# CI/piped/non-interactive runs).
trap '[ -t 0 ] && read -r -p "Press Enter to close..." _' EXIT

# The python of the venv is used directly (no activate script); without a venv the python on the PATH is used.
if [ -x .venv/bin/python ]; then
    VPY=".venv/bin/python"
elif [ -x .venv/Scripts/python.exe ]; then
    VPY=".venv/Scripts/python.exe"
else
    VPY="python3"
fi

if [ "$#" -eq 0 ]; then
    printf '%s\n' "No arguments given - running a real demo: validating the shipped example ToolRequest fixture."
    "$VPY" -m hydra_umc_local_technician.cli contracts validate tests/fixtures/tool_request.valid.json --contract ToolRequest
    status=$?
else
    "$VPY" -m hydra_umc_local_technician.cli "$@"
    status=$?
fi
exit "$status"
