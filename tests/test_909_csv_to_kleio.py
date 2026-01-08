# Test the transformation of a csv file into a kleio file

from datetime import datetime
import csv

from tests import TEST_DIR

from timelink.kleio.groups import KDate, KType, KValue, KReplace, KName, KSex
from timelink.kleio.groups import KKleio, KSource, KAct, KPerson
from timelink.kleio.groups.kls import KLs
from timelink.kleio.groups.katr import KAtr
from timelink.kleio.groups.kgroup import KGroup

csv_file_name = "leitura_bachareis.csv"
base_csv_filename = csv_file_name.replace('.csv', '')
csv_file_path = f"{TEST_DIR}/csv_data/{csv_file_name}"
kleio_file_path = f"{TEST_DIR}/timelink-home/projects/test-project/sources/csv_to_kleio"

# max rows to convert
max_rows = 23


def test_csv_to_kleio():

    # Extend the base Elements to get localized version
    KData = KDate.extend('data')  # noqa
    KSubstitui = KReplace.extend('substitui')  # noqa
    KTipo = KType.extend('tipo')  # noqa
    KValor = KValue.extend('valor')   # noqa
    KNome = KName.extend('nome')   # noqa
    KSexo = KSex.extend('sexo')   # noqa
    KEnd = KGroup.extend('end')   # noqa

    # Define localized sources based on Base Groups
    fonte = KSource.extend(
        "fonte", position=["id"], also=["tipo", "data", "ano", "substitui", "loc", "ref", "obs", "kleiofile"]
    )
    lista = KAct.extend(
        "lista",
        position=["id", "data"],
        guaranteed=["id"],
        also=["data", "tipo", "loc", "obs"],
    )

    bacharel = KPerson.extend("bacharel", position=["nome", "sexo"], guaranteed=["id", "nome", "sexo"], also=["mesmo_que", "obs"])
    ls = KLs.extend("ls", position=["type", "value", "date"], also=["obs", "entity"])
    atr = KAtr.extend("atr", position=["type", "value", "date"], also=["date", "obs", "entity"])

    # Part A
    # 1. read the csv values into a dict
    data = []
    with open(csv_file_path, mode="r", encoding="utf-8-sig") as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=";")
        for row in csv_reader:
            data.append(row)

    # 2. clean up the data. In this case we split dates which have
    #    some ranges in the form yyyy-mm-dd/yyyy-mm-dd in two fields

    for row in data:
        if "/" in row["Dates"]:
            dates = row["Dates"].split("/")
            row["first_date"] = dates[0].strip()
            row["last_date"] = dates[1].strip()
        else:  # if no / we set the two fields to the same value
            row["first_date"] = row["Dates"].strip()
            row["last_date"] = row["Dates"].strip()

    batch_min_date = min(row["first_date"] for row in data if row["Dates"])
    batch_max_date = max(row["last_date"] for row in data if row["Dates"])
    todays_date = datetime.today().strftime('%Y-%m-%d')

    batch_size = 10
    list_lb = lista("temp")  # we update this before writing the file
    for i, person in enumerate(data[:max_rows]):
        if i % batch_size == 0:
            if i > 0:
                # create Kleio and Source for this batch
                kleio = KKleio("gacto2.str")
                fonte_lb = fonte(f"{base_csv_filename}_{i // batch_size}", obs=f'Lido de {csv_file_name}')
                kleio.include(fonte_lb)
                # update the current list
                list_lb["id"] = f"{base_csv_filename}_l{i // batch_size}"
                list_lb["data"] = f"{batch_min_date}:{batch_max_date}"
                fonte_lb.include(list_lb)

                # Write the previous kleio content to a file
                file_path = f"{kleio_file_path}/" + f"{base_csv_filename}" + f"_{i // batch_size}.cli"
                with open(file_path, "w", encoding="utf-8") as kleio_file:
                    kleio_file.write(kleio.to_kleio())

                # create a new list for the next batch
                list_lb = lista("temp")

        p = bacharel(id=f"letbach-{i + 1}", nome=person["Name"], sexo='m')

        # Update min and max dates for the current batch
        if i % batch_size == 0:
            batch_min_date = person["first_date"]
            batch_max_date = person["last_date"]
        else:
            batch_min_date = min(batch_min_date, person["first_date"])
            batch_max_date = max(batch_max_date, person["last_date"])

        if person['first_date'] == person['last_date']:
            ls_date = person['first_date']
        else:
            ls_date = f"{person['first_date']}:{person['last_date']}"

        ls_leitura = ls("leitura-bacharel.data", person["Reference"], ls_date)
        atr_url = atr("leitura_bacharel.url", person["URL"], todays_date)
        p.include(ls_leitura)
        p.include(atr_url)

        list_lb.include(p)

    # Write the last batch of kleio content to a file
    file_path = f"{kleio_file_path}/" + f"{base_csv_filename}" + f"_{i // batch_size + 1}.cli"
    kleio = KKleio("gacto2.str")
    fonte_lb = fonte(f"{base_csv_filename}_{i // batch_size + 1}", obs=f'Lido de {csv_file_name}')
    kleio.include(fonte_lb)
    # update the current list
    list_lb["id"] = f"{base_csv_filename}_l{i // batch_size + 1}"
    list_lb["data"] = f"{batch_min_date}:{batch_max_date}"
    fonte_lb.include(list_lb)
    with open(file_path, "w", encoding="utf-8") as kleio_file:
        kleio_file.write(kleio.to_kleio())

    assert kleio.to_kleio() is not None
