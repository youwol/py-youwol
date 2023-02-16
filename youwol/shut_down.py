def shutdown_daemon_script(pid: int) -> str:
    return f"""#!/bin/sh
py_youwol_pid={pid}
kill $py_youwol_pid

success() {{
    echo "Successfully send kill signal"
    exit 0
}}

for i in 5 4 3 2 1 ; do
    kill -0 $py_youwol_pid 2> /dev/null || success
    echo "Still running … trying for $i second(s)"
    sleep 1
done
kill -0 $py_youwol_pid 2> /dev/null || success
echo "Failed to send kill signal"
exit 1
"""
