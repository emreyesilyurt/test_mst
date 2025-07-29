import csv
from sqlalchemy.orm import Session
from . import engine
from .manufacturer import Manufacturer
import os

CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), "manuf.csv")  # Adjust filename if needed

def import_manufacturers():
    session = Session(bind=engine)

    print("Starting import_manufacturers...")

    # Read CSV and collect distinct manuf and manuf_original values
    manuf_set = set()
    manuf_original_set = set()
    with open(CSV_FILE_PATH, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            manuf = row.get('manuf')
            manuf_original = row.get('manuf_original')
            if manuf:
                manuf_set.add(manuf.strip())
            if manuf_original:
                manuf_original_set.add(manuf_original.strip())

    print(f"Distinct 'manuf' values found: {len(manuf_set)}")
    print(f"Distinct 'manuf_original' values found: {len(manuf_original_set)}")

    # Save distinct manuf values as Manufacturer with id=manufacturer_id
    manuf_map = {}  # manuf name -> Manufacturer object
    for name in manuf_set:
        existing = session.query(Manufacturer).filter_by(name=name).first()
        if existing:
            manuf_map[name] = existing
        else:
            print(f"Adding manufacturer: {name}")
            m = Manufacturer(name=name)
            session.add(m)
            session.flush()  # to get id
            # Set manufacturer_id same as id
            m.manufacturer_id = m.id
            manuf_map[name] = m

    session.commit()
    print(f"Saved {len(manuf_map)} distinct 'manuf' manufacturers.")

    # Save distinct manuf_original values as Manufacturer with manufacturer_id pointing to manuf
    for original_name in manuf_original_set:
        existing = session.query(Manufacturer).filter_by(name=original_name).first()
        if existing:
            continue
        # Find parent manuf for this original_name by matching in CSV
        parent_name = None
        with open(CSV_FILE_PATH, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('manuf_original', '').strip() == original_name:
                    parent_name = row.get('manuf', '').strip()
                    break
        if parent_name and parent_name in manuf_map:
            parent = manuf_map[parent_name]
            m = Manufacturer(name=original_name, manufacturer_id=parent.id)
            session.add(m)
        else:
            # If no parent found, just add with manufacturer_id = None
            m = Manufacturer(name=original_name)
            session.add(m)

    session.commit()
    print(f"Saved distinct 'manuf_original' manufacturers.")
    session.close()

if __name__ == "__main__":
    import_manufacturers()
