echo We need to create config for this server. It must be saved as \"config.yaml\" in workdir of server
echo -n "Enter tcp port (1001 - 65000) [default: 8008]: "
read port
if [[ "$port" == "" ]]; then
port="8008"
fi
echo "port: \"$port\"" > .temp.yaml
echo -n "Enter input endpoint relative path [default: \"/ws\"]: "
read endpoint
if [[ "$endpoint" == "" ]]; then
endpoint="/ws"
fi
echo "websocket_path: \"$endpoint\"" >> .temp.yaml

userscnt="0"
function inputUser {
    if [[ "$userscnt" == "0" ]]; then
    echo -n "Enter first user login: "
    read login
    if [[ "$login" == "" ]]; then
    echo "You MUST enter username for first user"
    return
    fi
    echo -n "Enter first user password: "
    read password
    else
        echo -n "Enter next user login (leave empty to skip): "
    read login
    if [[ "$login" == "" ]]; then
    userscnt="-1"
    return
    fi
    echo -n "Enter first user password: "
    read password
    fi
    userscnt=$(( $userscnt + 1 ))
    echo "  - username: \"$login\"" >> .temp.yaml
    echo "    password: \"$password\"">> .temp.yaml
}

echo "users:" >> .temp.yaml

while [[ "$userscnt" != "-1" ]]
do
inputUser
done

cat >> .temp.yaml <<EOL
outputs:
  - type: "stdout"
    level: 0
EOL
echo "Add file output? To add just enter path to file: "
read path
if [[ "$path" != "" ]]; then
cat >> .temp.yaml <<EOL
  - type: "fileout"
    level: 0
    path: "$path"
EOL
fi



echo -n "Done! do you want move result to current dir as config.yaml (y/n)? "
read ans
if [[ "$ans" == 'y' ]]
then
mv .temp.yaml config.yaml
else
echo -e "\nNot moved. There is the content:\n"
cat .temp.yaml
fi