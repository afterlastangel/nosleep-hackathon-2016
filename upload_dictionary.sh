for entry in data/$1/*
do
    filename="${PWD}/$entry"
    echo $filename
    curl -X POST --form file=@$filename http://nosleep-1469844138323.appspot.com/v1/dictionary?index_name=shakespeare
done

