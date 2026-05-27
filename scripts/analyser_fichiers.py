#!/usr/bin/env python3
# Script à lancer dans ton venv activé
# Usage : python scripts/analyser_fichiers.py

import pandas as pd
import os
import glob

# Chemin vers tes fichiers
DATASETS_DIR = "/home/zeinab/backend_medical_ia/datasets"

# Trouver tous les fichiers xlsx et csv
fichiers = glob.glob(f"{DATASETS_DIR}/*.xlsx") + glob.glob(f"{DATASETS_DIR}/*.csv")

if not fichiers:
    print("❌ Aucun fichier trouvé dans", DATASETS_DIR)
    print("   Vérifie que tu as bien copié tes fichiers.")
    exit()

print(f"✓ {len(fichiers)} fichiers trouvés\n")
print("=" * 60)

for chemin in sorted(fichiers):
    nom = os.path.basename(chemin)
    
    # Lire le fichier
    try:
        if chemin.endswith('.xlsx'):
            df = pd.read_excel(chemin)
        else:
            # Essayer différents encodages
            try:
                df = pd.read_csv(chemin, encoding='utf-8')
            except:
                df = pd.read_csv(chemin, encoding='latin-1')
        
        print(f"\n📋 TABLE : {nom}")
        print(f"   Lignes : {len(df):,} | Colonnes : {len(df.columns)}")
        print(f"\n   Colonnes détectées :")
        
        for col in df.columns:
            dtype = df[col].dtype
            nulls = df[col].isnull().sum()
            pct_null = (nulls / len(df) * 100)
            exemple = df[col].dropna().iloc[0] if len(df[col].dropna()) > 0 else "(vide)"
            null_info = f" [{pct_null:.0f}% null]" if pct_null > 0 else ""
            print(f"   → {col:<30} {str(dtype):<12} ex: {str(exemple)[:30]}{null_info}")
        
        print("-" * 60)
    
    except Exception as e:
        print(f"\n❌ Erreur avec {nom}: {e}")

print("\n✓ Analyse terminée ! Copie la sortie pour créer tes tables SQL.")