from back_office.routing import Page

from .callbacks import add_callbacks
from .layout import layout

PAGE: Page = Page(layout, add_callbacks, login_required=True)

# En cas d'édition, montrer le différentiel entre le texte initial et le texte édité
# TODO : ajouter le bouton 'Enregistrer' et implémenter le callback associé : ne pas perder les thèmes et autre
# TODO : avoir seulement des structured AM
# TODO : ajouter un bouton aperçu pour les tableaux
# TODO : refaire l'édition des paramètres
# TODO : factoriser _count_prefix_hashtags
# TODO : ajouter des tests sur les fonctions importantes
