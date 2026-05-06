CREATE TABLE IF NOT EXISTS bisac (
    id_bisac INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL,
    categoria VARCHAR(255),
    tag_shopify VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS onix (
    id_onix INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    tipo_tapa VARCHAR(50),
    titulo VARCHAR(255),
    autor VARCHAR(255),
    lenguaje VARCHAR(50),
    audiencia VARCHAR(50),
    descripcion TEXT,
    url_tapa TEXT,
    editorial VARCHAR(255),

    id_archivo INTEGER,

    CONSTRAINT fk_onix_archivo
    FOREIGN KEY (id_archivo)
    REFERENCES archivo(id_archivo)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

CREATE TABLE archivo (
    id_archivo INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT,
    proveedor TEXT,
    onix_version TEXT
);