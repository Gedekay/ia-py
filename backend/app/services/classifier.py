from app.models.document import TypePiece


CLASSIFICATION_KEYWORDS: dict[TypePiece, tuple[str, ...]] = {
    TypePiece.NOTIFICATION_DROITS: ("notification des droits", "droits du suspect"),
    TypePiece.CERTIFICAT_MEDICAL: ("certificat médical", "certificat medico"),
    TypePiece.INTERROGATOIRE: ("interrogatoire", "audition du suspect"),
    TypePiece.TEMOIGNAGE: ("témoignage", "declaration du temoin", "déclaration du témoin"),
    TypePiece.SAISIE: ("procès-verbal de saisie", "pv de saisie", "inventaire des objets saisis"),
    TypePiece.EXPERTISE: ("rapport d'expertise", "expertise technique"),
    TypePiece.PROCES_VERBAL: ("procès-verbal", "proces-verbal", "pv de plainte"),
}


def classify_piece(text: str, filename: str = "") -> TypePiece:
    source = f"{filename}\n{text}".casefold()
    for piece_type, keywords in CLASSIFICATION_KEYWORDS.items():
        if any(keyword in source for keyword in keywords):
            return piece_type
    return TypePiece.AUTRE