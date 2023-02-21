def shutdown_daemon_script(pid: int) -> str:
    return f"""#!/bin/sh
py_youwol_pid={pid}

success() {{
    echo "Gracefully stopped $py_youwol_pid with TERM signal"
    exit 0
}}

warn() {{
    echo "Hard killed $py_youwol_pid with KILL signal"
    exit 1
}}

echo "Sending TERM signal to $py_youwol_pid"
kill $py_youwol_pid
for i in 60 55 50 45 40 35 30 25 20 15 10 5 ; do
    kill -0 $py_youwol_pid 2> /dev/null || success
    echo "Still running … waiting $i seconds before sending KILL"
    sleep 5
done
kill -0 $py_youwol_pid 2> /dev/null || success
echo "Failed to send TERM signal to py-youwol"

echo "Sending KILL signal to $py_youwol_pid"
kill -KILL $py_youwol_pid
for i in 60 55 50 45 40 35 30 25 20 15 10 5 ; do
    kill -0 $py_youwol_pid 2> /dev/null || warn
    echo "Still running … waiting $i seconds before failing"
    sleep 5
done
kill -0 $py_youwol_pid 2> /dev/null || warn
echo "Failed to send KILL signal to py-youwol"
exit 1
"""
