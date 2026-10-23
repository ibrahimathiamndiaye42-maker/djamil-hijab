PERMISSIONS = {
    "products.read": "Consulter les produits",
    "products.write": "Créer / modifier / désactiver les produits",
    "categories.write": "Gérer les catégories",
    "stock.read": "Consulter le stock et les mouvements",
    "stock.entry": "Enregistrer des arrivages",
    "stock.adjust": "Corriger le stock (perte, casse, correction, retours)",
    "suppliers.read": "Consulter les fournisseurs",
    "suppliers.write": "Gérer les fournisseurs",
    "customers.read": "Consulter les clients",
    "customers.write": "Créer / modifier les clients",
    "sales.create": "Enregistrer des ventes",
    "sales.read": "Consulter ses propres ventes et factures",
    "sales.read_all": "Consulter toutes les ventes et factures",
    "sales.cancel": "Annuler une facture (avoir)",
    "inventories.run": "Effectuer des inventaires",
    "control.read": "Consulter le contrôle des écarts",
    "audit.read": "Consulter le journal d'activité",
    "reports.read": "Consulter le tableau de bord et les rapports",
    "settings.write": "Modifier les paramètres",
    "users.manage": "Gérer les utilisateurs",
}
EMPLOYEE_DEFAULTS = ["products.read", "stock.read", "customers.read", "customers.write",
                     "sales.create", "sales.read"]

# signe attendu du delta ; 0 = positif ou négatif accepté
MOVEMENT_SIGN = {"ENTREE": 1, "RETOUR_CLIENT": 1, "VENTE": -1, "RETOUR_FOURNISSEUR": -1,
                 "ENDOMMAGE": -1, "PERTE": -1, "CORRECTION": 0, "INVENTAIRE": 0}
REASON_REQUIRED = {"CORRECTION", "PERTE", "ENDOMMAGE", "INVENTAIRE", "RETOUR_FOURNISSEUR"}

DEFAULT_SETTINGS = {
    "company_name": "DJAMIL HIJAB",
    "phones": ["77 238 66 70", "70 840 12 25", "33 837 53 84"],
    "address": "",
    "currency": "FCFA",
    "payment_methods": ["Espèces", "Wave", "Orange Money", "Carte", "Autre"],
    "invoice_footer": "Merci pour votre confiance.",
    "logo_url": "",
}
DEFAULT_CATEGORIES = ["Voiles", "Hijabs", "Robes", "Accessoires", "Autres"]
