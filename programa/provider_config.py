#!/usr/bin/env python3

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Configuration for CSV data providers."""

    name: str
    """Provider name (e.g., 'planeta', 'penguin', etc.)"""

    delimiter: str
    """CSV delimiter character (e.g., ',', ';')"""

    field_mapping: dict[str, str]
    """Map from internal field names to CSV column names.
    
    Required fields:
    - isbn: ISBN column name
    - titulo: Title column name
    - autor: Author column name
    - tipo_tapa: Cover type column name
    - lenguaje: Language column name
    - audiencia: Audience column name
    - descripcion: Description column name
    - url_tapa: Cover URL column name
    - editorial: Publisher column name
    - tag: Tag/Category column name
    """


# Planeta provider configuration
PLANETA = ProviderConfig(
    name="planeta",
    delimiter=";",
    field_mapping={
        "isbn": "EAN",
        "titulo": "TITULO",
        "autor": "AUTORES",
        "tipo_tapa": "PRESENTACION",  # Tipo de producto/presentación
        "lenguaje": "IDIOMA_PUBLICACION",
        "audiencia": "NARRACION",  # Not available in Planeta CSV
        "descripcion": "SINOPSIS",
        "url_tapa": "PORTADA",
        "editorial": "SELLO",
        "tag": "IBIC",  # Use IBIC codes instead of TAG_DESCRIPTIVOS
    },
)

# List of all available providers
PROVIDERS = {
    "planeta": PLANETA,
}


def detect_provider_by_delimiter(first_line: str) -> ProviderConfig | None:
    """Detect provider by analyzing the first line (header).
    
    Args:
        first_line: First line of CSV file (header row)
    
    Returns:
        ProviderConfig if detected, None otherwise
    """
    for provider in PROVIDERS.values():
        if provider.delimiter in first_line:
            # Validate that key fields exist in header
            columns = first_line.split(provider.delimiter)
            columns = [col.strip() for col in columns]
            
            required_fields = [
                "isbn",
                "titulo",
                "descripcion",
            ]
            
            missing = []
            for field_name in required_fields:
                csv_name = provider.field_mapping.get(field_name)
                if csv_name and csv_name not in columns:
                    missing.append(csv_name)
            
            if not missing:
                return provider
    
    return None


def get_provider(name: str) -> ProviderConfig | None:
    """Get provider configuration by name.
    
    Args:
        name: Provider name (lowercase)
    
    Returns:
        ProviderConfig if found, None otherwise
    """
    return PROVIDERS.get(name.lower())
