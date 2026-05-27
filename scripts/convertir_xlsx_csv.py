#!/usr/bin/env python3
# Convertit tous les XLSX en CSV prêts pour PostgreSQL

import pandas as pd
import os
import glob

DATASETS_DIR = "/home/zeinab/backend_medical_ia/datasets"

fichiers_xlsx = glob.glob(f"{DATASETS_DIR}/*.xlsx")

if not fichiers_xlsx:
    print("Aucun fichier XLSX trouvé — tes fichiers sont peut-être déjà en CSV ?")
    exit()

print(f"Conversion de {len(fichiers_xlsx)} fichiers XLSX → CSV\n")

for chemin_xlsx in sorted(fichiers_xlsx):
    nom = os.path.basename(chemin_xlsx)
    nom_csv = nom.replace('.xlsx', '.csv')
    chemin_csv = os.path.join(DATASETS_DIR, nom_csv)
    
    try:
        # Lire le fichier Excel
        df = pd.read_excel(chemin_xlsx)
        
        # Nettoyer les noms de colonnes (enlever espaces, caractères spéciaux)
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]
        
        # Sauvegarder en CSV UTF-8 (PostgreSQL le supporte bien)
        df.to_csv(chemin_csv, index=False, encoding='utf-8')
        
        print(f"✓ {nom} → {nom_csv}  ({len(df):,} lignes, {len(df.columns)} colonnes)")
        print(f"  Colonnes : {', '.join(df.columns)}")
        print()
    
    except Exception as e:
        print(f"✗ Erreur avec {nom}: {e}")

print("\n✓ Conversion terminée ! Tes CSV sont dans :", DATASETS_DIR)