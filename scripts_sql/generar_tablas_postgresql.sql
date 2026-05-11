CREATE TABLE IF NOT EXISTS bisac (
    id_bisac INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    codigo VARCHAR(20) NOT NULL,
    categoria VARCHAR(255),
    tag_shopify VARCHAR(255),
    tag_shopify_ingles TEXT;
);

CREATE TABLE IF NOT EXISTS metadato (
    id_metadato INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    isbn VARCHAR(20) NOT NULL UNIQUE,
    tipo_tapa VARCHAR(50),
    titulo TEXT,
    autor VARCHAR(255),
    lenguaje VARCHAR(50),
    audiencia VARCHAR(50),
    descripcion TEXT,
    url_tapa TEXT,
    editorial VARCHAR(255),
    tag TEXT,

    id_archivo INTEGER,

    CONSTRAINT fk_metadato_archivo
    FOREIGN KEY (id_archivo)
    REFERENCES archivo(id_archivo)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);

CREATE TABLE archivo (
    id_archivo INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre TEXT UNIQUE,
    proveedor TEXT,
    onix_version TEXT
);

CREATE TABLE idioma (
    id_idioma INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    idioma TEXT,
    valor_shopify TEXT
);

CREATE TABLE tapa (
    id_tapa INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tapa TEXT,
    valor_shopify TEXT
);

CREATE TABLE audiencia (                                 
    id_audiencia INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    audiencia TEXT,
    valor_shopify TEXT
);

CREATE TABLE raw (
    id_raw INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    isbn TEXT UNIQUE,
    tipo_tapa TEXT,
    titulo TEXT,
    autor TEXT,
    lenguaje TEXT,
    audiencia TEXT,
    descripcion TEXT,
    url_tapa TEXT,
    editorial TEXT,
    tag TEXT,

    id_archivo INTEGER,

    CONSTRAINT fk_raw_archivo
    FOREIGN KEY (id_archivo)
    REFERENCES archivo(id_archivo)
    ON DELETE SET NULL
    ON UPDATE CASCADE
);
