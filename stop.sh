process=($(ps -A | grep python3))
declare -p process
process_id=${process[0]}
kill $process_id
