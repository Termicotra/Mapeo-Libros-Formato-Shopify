-- Script de carga de tablas auxiliares
-- Generado automáticamente desde la base de datos actual
BEGIN;

TRUNCATE TABLE bisac, audiencia, idioma, tapa RESTART IDENTITY;

-- Datos de bisac
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC', 'Fiction / General', 'ficcion', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC004', 'Fiction / Classics', 'ficcion, literatura, clasicos', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('POE000', 'Poetry / General', 'ficcion, literatura, poesia', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('PER011', 'Performing Arts / Theater / General', 'ficcion, literatura, teatro', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC029', 'Fiction / Short Stories (single author)', 'ficcion, literatura, cuentos cortos', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC019', 'Fiction / Literary', 'ficcion, generos literarios', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC027', 'Fiction / Romance / General', 'ficcion, generos literarios, novela romantica', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC014', 'Fiction / Historical', 'ficcion, generos literarios, novela historica', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC028', 'Fiction / Science Fiction / General', 'ficcion, generos literarios, fantastica y ciencia ficcion, fantastica, ciencia ficcion', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC030', 'Fiction / Thrillers / Suspense', 'ficcion, generos literarios, misterio y suspenso, misterio, suspenso', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC022', 'Fiction / Mystery & Detective / General', 'ficcion, generos literarios, misterio y suspenso, misterio, suspenso', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('CGN', 'Comics & Graphic Novels / General', 'ficcion, novela grafica', 'fiction, graphic novels');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('SCI', 'Science / General', 'no ficcion, ciencias y tecnologia, ciencias, cientifica', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('SCI086', 'Science / Life Sciences / General', 'no ficcion, ciencias y tecnologia, medicina y salud, salud', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('SEL', 'Self-Help / General', 'no ficcion, humanidades, autoayuda, espiritualidad', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('OCC', 'Body, Mind & Spirit / General', 'no ficcion, humanidades, autoayuda, espiritualidad', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('BUS', 'Business & Economics / General', 'no ficcion, humanidades, economia, empresa', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('PSY', 'Psychology / General', 'no ficcion, humanidades, psicologia', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('EDU', 'Education / General', 'no ficcion, humanidades, pedagogia', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('BIO', 'Biography & Autobiography / General', 'no ficcion, historia, biografias', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('HIS', 'History / General', 'no ficcion, historia, historias', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('ART', 'Art / General', 'no ficcion, arte', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('ART057', 'Art / Film & Video', 'no ficcion, arte, fotografia', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('ARC', 'Architecture / General', 'no ficcion, arte, arquitectura', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('PER004', 'Performing Arts / Film & Video / General', 'no ficcion, arte, cine', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('DES', 'Design / General', 'no ficcion, arte, diseno, moda', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('ART015', 'Art / History / General', 'no ficcion, arte, historia del arte', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('MUS', 'Music / General', 'no ficcion, arte, musica', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('CKB', 'Cooking / General', 'no ficcion, estilo de vida, libros de cocina, cocina', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('SPO', 'Sports & Recreation / General', 'no ficcion, estilo de vida, deportes', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('PER', 'Performing Arts / General', 'no ficcion, estilo de vida, entretenimiento', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('CRA', 'Crafts & Hobbies / General', 'no ficcion, estilo de vida, manualidades', 'non fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('JUV038', 'Juvenile Fiction / Short Stories', 'infantil, libros infantiles, cuentos infantiles', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('JUV008', 'Juvenile Fiction / Comics & Graphic Novels / General', 'infantil, novela grafica ninos', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('GAM001', 'Games / Board', 'infantil, juegos de mesa', ' ');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('GAM005', 'Games / Logic & Brain Teasers', 'infantil, juegos didacticos, otros, papeleria y merchandising, juegos y puzzles', ' ');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('GAM007', 'Games / Puzzles', 'infantil, rompecabezas, otros, papeleria y merchandising, juegos y puzzles', ' ');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('JNF019', 'Juvenile Nonfiction / Family / General', 'infantil, imprescindibles infantiles, crianza positiva - valores', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FAM016', 'Family & Relationships / Education', 'infantil, imprescindibles infantiles, crianza positiva - valores', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('JUV031', 'Juvenile Fiction / Performing Arts / General', 'infantil, imprescindibles infantiles, personajes infantiles', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('JUV040', 'Juvenile Fiction / Toys, Dolls, Puppets', 'infantil, imprescindibles infantiles, personajes infantiles', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('YAF', 'Young Adult Fiction', 'juvenil, jovenes lectores', 'books in english for young adults');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('YAN', 'Young Adult Non Fiction', 'juvenil, jovenes lectores', 'books in english for young adults');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('YAF026', 'Young Adult Fiction / Horror', 'juvenil, jovenes lectores, novela de terror', 'books in english for young adults');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('JUV', 'Juvenile Fiction', 'infantil', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('JNF', 'Juvenile Non Fiction', 'infantil', 'books in english for kids');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC042100', 'Fiction / Christian / Contemporary', 'ficcion, literatura, contemporanea', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC009010', 'Fiction / Fantasy / Contemporary', 'ficcion, literatura, contemporanea', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('FIC027020', 'Fiction / Romance / Contemporary', 'ficcion, literatura, contemporanea, generos literarios, novela romantica', 'fiction');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('', 'default', 'todos los libros', ' ');
INSERT INTO bisac (codigo, categoria, tag_shopify, tag_shopify_ingles) VALUES ('', 'ingles', 'books in english', ' ');

-- Datos de audiencia
INSERT INTO audiencia (audiencia, valor_shopify) VALUES ('infantil', 'infantil');
INSERT INTO audiencia (audiencia, valor_shopify) VALUES ('juvenil', 'juvenil');

-- Datos de idioma
INSERT INTO idioma (idioma, valor_shopify) VALUES ('Espanol', 'spa-spanish');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('Español', 'spa-spanish');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('Español (ES)', 'spa-spanish');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('spa', 'spa-spanish');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('spanish', 'spa-spanish');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('ES', 'spa-spanish');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('Inglés', 'eng-english');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('Inglés (IN)', 'eng-english');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('Ingles', 'eng-english');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('eng', 'eng-english');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('english', 'eng-english');
INSERT INTO idioma (idioma, valor_shopify) VALUES ('EN', 'eng-english');

-- Datos de tapa
INSERT INTO tapa (tapa, valor_shopify) VALUES ('BB', 'tapa-dura');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('BC', 'tapa-blanda');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('Rústica ', 'tapa-blanda');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('Tapa dura', 'tapa-dura');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('Grapa', 'other');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('Todo cartón', 'other');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('Dura', 'tapa-dura');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('Blanda', 'tapa-blanda');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('TD', 'tapa-dura');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('R', 'tapa-blanda');
INSERT INTO tapa (tapa, valor_shopify) VALUES ('B', 'tapa-blanda');

COMMIT;
