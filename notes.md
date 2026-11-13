Co się stanie, gdy Ceneo zablokuje skrypt? Skąd się dowiem?
Dlaczego cena zapisuje się po sprawdzeniu minimum?
Co robi parse_price i dlaczego ma tyle wyjątków na spacje?

1. Dowiem sie z pliku z logami. Petla leci dalej, nie przerywa sie
2. Poniewaz sprypt sprawdza w bazie minimum i porownuje je z aktualnym wpisem, gdyby aktualny wpis juz byl w bazie wtedy min==aktualny wpis
3. cena moze byc zapisana w roznej konfiguracji
