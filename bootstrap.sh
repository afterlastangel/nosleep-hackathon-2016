VIRTUALENV_FOLDER='venv'
virtualenv $VIRTUALENV_FOLDER
if [ ! -d $VIRTUALENV_FOLDER ];
then
  virtualenv $VIRTUALENV_FOLDER
fi
. $VIRTUALENV_FOLDER/bin/activate
pip install -r requirements.dev.txt
pip install -r requirements.txt -t lib
pip install -r requirements.txt

