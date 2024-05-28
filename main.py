from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from SPARQLWrapper import SPARQLWrapper, JSON
from rdflib import Graph, URIRef, Literal

app = FastAPI()
templates = Jinja2Templates(directory="templates")
fuseki_url = "http://localhost:3030/Biblioteca"

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/home")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/insertar_libro")
async def mostrar_formulario_insertar_libro(request: Request):
    return templates.TemplateResponse("insertar_libro.html", {"request": request})

@app.post("/insertar_libro")
async def insertar_libro(request: Request):
    
    form_data = await request.form()
    titulo = form_data["titulo"]
    autor = form_data["autor"]
    categoria = form_data["categoria"]
    tipo = form_data["tipo"]
    editorial = form_data["editorial"]

    # Conexión a la base de datos SPARQL
    sparql = SPARQLWrapper(fuseki_url)

    # Obtener el ID del autor
    consulta_autor = f"""
        PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>
        SELECT ?autor
        WHERE {{
            ?autor a biblio:Autor ;
                   biblio:nombrePersona "{autor}"@es .
        }}
    """
    sparql.setQuery(consulta_autor)
    sparql.setReturnFormat(JSON)
    resultados_autor = sparql.query().convert()

    if resultados_autor["results"]["bindings"]:
        autor_uri = resultados_autor["results"]["bindings"][0]["autor"]["value"]
    else:
        # Si el autor no existe, insertarlo en la ontología
        consulta_insertar_autor = f"""
            PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>
            INSERT DATA {{
                biblio:autor_{autor.replace(" ", "_")} a biblio:Autor ;
                    biblio:nombrePersona "{autor}"@es .
            }}
        """
        sparql.setQuery(consulta_insertar_autor)
        sparql.method = "POST"
        sparql.query()
        autor_uri = f"http://www.semanticweb.org/kevin/ontologies/biblioteca/autor_{autor.replace(' ', '_')}"

    # Obtener el ID de la categoría
    consulta_categoria = f"""
        PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>
        SELECT ?categoria
        WHERE {{
            ?categoria a biblio:Categoria ;
                       biblio:nombreCategoria "{categoria}"@es .
        }}
    """
    sparql.setQuery(consulta_categoria)
    sparql.setReturnFormat(JSON)
    resultados_categoria = sparql.query().convert()

    if resultados_categoria["results"]["bindings"]:
        categoria_uri = resultados_categoria["results"]["bindings"][0]["categoria"]["value"]
    else:
        # Si la categoría no existe, insertarla en la ontología
        consulta_insertar_categoria = f"""
            PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>
            INSERT DATA {{
                biblio:categoria_{categoria.replace(" ", "_")} a biblio:Categoria ;
                    biblio:nombreCategoria "{categoria}"@es .
            }}
        """
        sparql.setQuery(consulta_insertar_categoria)
        sparql.method = "POST"
        sparql.query()
        categoria_uri = f"http://www.semanticweb.org/kevin/ontologies/biblioteca/categoria_{categoria.replace(' ', '_')}"

    # Obtener el ID de la editorial
    consulta_editorial = f"""
        PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>
        SELECT ?editorial
        WHERE {{
            ?editorial a biblio:Editorial ;
                       biblio:nombreEditorial "{editorial}"@es .
        }}
    """
    sparql.setQuery(consulta_editorial)
    sparql.setReturnFormat(JSON)
    resultados_editorial = sparql.query().convert()

    if resultados_editorial["results"]["bindings"]:
        editorial_uri = resultados_editorial["results"]["bindings"][0]["editorial"]["value"]
    else:
        # Si la editorial no existe, insertarla en la ontología
        consulta_insertar_editorial = f"""
            PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>
            INSERT DATA {{
                biblio:editorial_{editorial.replace(" ", "_")} a biblio:Editorial ;
                    biblio:nombreEditorial "{editorial}"@es .
            }}
        """
        sparql.setQuery(consulta_insertar_editorial)
        sparql.method = "POST"
        sparql.query()
        editorial_uri = f"http://www.semanticweb.org/kevin/ontologies/biblioteca/editorial_{editorial.replace(' ', '_')}"

    # Construcción de la consulta de inserción
    consulta_insertar_libro = f"""
        PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

        INSERT DATA {{
            biblio:libro_{titulo.replace(" ", "_")} a biblio:Libro ;
                biblio:Titulo "{titulo}"@es ;
                biblio:tieneAutor <{autor_uri}> ;
                biblio:perteneceCategoria <{categoria_uri}> ;
                biblio:Tipo "{tipo}"@es ;
                biblio:publicadoPor <{editorial_uri}> .
        }}
    """

    # Ejecución de la consulta
    sparql.setQuery(consulta_insertar_libro)
    sparql.method = "POST"
    sparql.query()

    return RedirectResponse(f"/home?exito=Libro+insertado+correctamente", status_code=303)




@app.get("/autores-populares")
def get_autores_populares(request: Request):
    consulta = """
    PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

    SELECT ?autorNombre (COUNT(?libro) AS ?cantidadLibros)
    WHERE {
        ?autor a biblio:Autor ;
               biblio:nombrePersona ?autorNombre .
        ?libro biblio:tieneAutor ?autor ;
               biblio:publicadoPor ?editorial .
        FILTER regex(?autorNombre, "", "i")
    }
    GROUP BY ?autorNombre
    ORDER BY DESC(?cantidadLibros)
    """
    sparql = SPARQLWrapper(fuseki_url)
    sparql.setQuery(consulta)
    sparql.setReturnFormat(JSON)
    resultados = sparql.query().convert()
    autores = [{"autorNombre": r["autorNombre"]["value"], "cantidadLibros": r["cantidadLibros"]["value"]} for r in resultados["results"]["bindings"]]
    return templates.TemplateResponse("index.html", {"request": request, "autores": autores})

@app.get("/libros")
def get_libros(request: Request):
    consulta = """
    PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

    SELECT ?titulo ?autorNombre ?categoriaNombre ?tipo ?nombreEditorial
    WHERE {
        {
            ?libro a biblio:Libro .
            BIND("Libro" AS ?tipo)
        } UNION {
            ?libro a biblio:libroAntiguo .
            BIND("Antiguo" AS ?tipo)
        } UNION {
            ?libro a biblio:libroModerno .
            BIND("Moderno" AS ?tipo)
        }
        ?libro biblio:Titulo ?titulo ;
               biblio:tieneAutor ?autor ;
               biblio:perteneceCategoria ?categoria ;
               biblio:publicadoPor ?editorial .
        ?autor biblio:nombrePersona ?autorNombre .
        ?categoria biblio:nombreCategoria ?categoriaNombre .
        ?editorial biblio:nombreEditorial ?nombreEditorial .
        FILTER regex(?titulo, "", "i")
    }
    ORDER BY ?titulo
    """
    sparql = SPARQLWrapper(fuseki_url)
    sparql.setQuery(consulta)
    sparql.setReturnFormat(JSON)
    resultados = sparql.query().convert()
    libros = [{"titulo": r["titulo"]["value"],
               "autorNombre": r["autorNombre"]["value"],
               "categoriaNombre": r["categoriaNombre"]["value"],
               "tipo": r["tipo"]["value"],
               "nombreEditorial": r["nombreEditorial"]["value"]} for r in resultados["results"]["bindings"]]
    return templates.TemplateResponse("libros.html", {"request": request, "libros": libros})

@app.get("/prestamos-vencidos")
def get_prestamos_vencidos(request: Request):
    consulta = """
    PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

    SELECT ?nombreCliente ?fechaDevolucion (COUNT(?prestamo) AS ?numPrestamosVencidos)
    WHERE {
        ?cliente a biblio:Cliente ;
                 biblio:idPersona ?idCliente ;
                 biblio:nombrePersona ?nombreCliente .
        ?prestamo a biblio:Prestamo ;
                  biblio:involucraCliente ?cliente ;
                  <http://www.semanticweb.org/kevin/ontologies/biblioteca#fechaDevolucion> ?fechaDevolucion .
        FILTER (?fechaDevolucion < now())
        FILTER regex(?nombreCliente, "", "i")
    }
    GROUP BY ?nombreCliente ?fechaDevolucion
    """
    sparql = SPARQLWrapper(fuseki_url)
    sparql.setQuery(consulta)
    sparql.setReturnFormat(JSON)
    resultados = sparql.query().convert()
    prestamos_vencidos = [{"nombreCliente": r["nombreCliente"]["value"],
                           "fechaDevolucion": r["fechaDevolucion"]["value"],
                           "numPrestamosVencidos": r["numPrestamosVencidos"]["value"]} for r in resultados["results"]["bindings"]]
    return templates.TemplateResponse("prestamos_vencidos.html", {"request": request, "prestamos_vencidos": prestamos_vencidos})

@app.get("/editoriales-populares")
def get_editoriales_populares(request: Request):
    consulta = """
    PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

    SELECT ?nombreEditorial (COUNT(?libro) AS ?cantidadLibros)
    WHERE {
        ?editorial a biblio:Editorial ;
                   biblio:nombreEditorial ?nombreEditorial .
        ?libro biblio:publicadoPor ?editorial .
        FILTER regex(?nombreEditorial, "", "i")
    }
    GROUP BY ?nombreEditorial
    ORDER BY DESC(?cantidadLibros)
    """
    sparql = SPARQLWrapper(fuseki_url)
    sparql.setQuery(consulta)
    sparql.setReturnFormat(JSON)
    resultados = sparql.query().convert()
    editoriales = [{"nombreEditorial": r["nombreEditorial"]["value"], "cantidadLibros": r["cantidadLibros"]["value"]} for r in resultados["results"]["bindings"]]
    return templates.TemplateResponse("editoriales_populares.html", {"request": request, "editoriales": editoriales})

@app.get("/libros-por-idioma")
def get_libros_por_idioma(request: Request):
    consulta = """
    PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

    SELECT ?idioma (COUNT(?libro) AS ?cantidadLibros)
    WHERE {
        ?libro biblio:Idioma ?idioma .
        FILTER regex(?idioma, "", "i")
    }
    GROUP BY ?idioma
    ORDER BY DESC(?cantidadLibros)
    """
    sparql = SPARQLWrapper(fuseki_url)
    sparql.setQuery(consulta)
    sparql.setReturnFormat(JSON)
    resultados = sparql.query().convert()
    libros_por_idioma = [{"idioma": r["idioma"]["value"], "cantidadLibros": r["cantidadLibros"]["value"]} for r in resultados["results"]["bindings"]]
    return templates.TemplateResponse("libros_por_idioma.html", {"request": request, "libros_por_idioma": libros_por_idioma})

@app.get("/prestamos-por-cliente")
def get_prestamos_por_cliente(request: Request):
    consulta = """
    PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

    SELECT ?nombreCliente ?fechaDevolucion (COUNT(?prestamo) AS ?numPrestamosVencidos)
    WHERE {
        ?cliente a biblio:Cliente ;
                 biblio:idPersona ?idCliente ;
                 biblio:nombrePersona ?nombreCliente .
        ?prestamo a biblio:Prestamo ;
                  biblio:involucraCliente ?cliente ;
                  <http://www.semanticweb.org/kevin/ontologies/biblioteca#fechaDevolucion> ?fechaDevolucion .
        FILTER (?fechaDevolucion < now())
        FILTER regex(?nombreCliente, "", "i")
    }
    GROUP BY ?nombreCliente ?fechaDevolucion
    """
    sparql = SPARQLWrapper(fuseki_url)
    sparql.setQuery(consulta)
    sparql.setReturnFormat(JSON)
    resultados = sparql.query().convert()
    prestamos_por_cliente = [{"nombreCliente": r["nombreCliente"]["value"], "fechaDevolucion": r["fechaDevolucion"]["value"], "numPrestamosVencidos": r["numPrestamosVencidos"]["value"]} for r in resultados["results"]["bindings"]]
    return templates.TemplateResponse("prestamos_por_cliente.html", {"request": request, "prestamos_por_cliente": prestamos_por_cliente})

@app.get("/libros-prestados")
def get_libros_prestados(request: Request):
    consulta = """
    PREFIX biblio: <http://www.semanticweb.org/kevin/ontologies/biblioteca/>

    SELECT ?titulo ?clienteNombre ?tipo ?fechaPrestamo ?fechaDevolucion
    WHERE {
        ?prestamo a biblio:Prestamo ;
                  biblio:involucraLibro ?libro ;
                  biblio:involucraCliente ?cliente ;
                  biblio:fechaPrestamo ?fechaPrestamo ;
                  <http://www.semanticweb.org/kevin/ontologies/biblioteca#fechaDevolucion> ?fechaDevolucion .
        {
            ?libro a biblio:Libro .
            BIND("Libro" AS ?tipo)
        } UNION {
            ?libro a biblio:libroAntiguo .
            BIND("Antiguo" AS ?tipo)
        } UNION {
            ?libro a biblio:libroModerno .
            BIND("Moderno" AS ?tipo)
        }
        ?libro biblio:Titulo ?titulo .
        ?cliente biblio:nombrePersona ?clienteNombre .
    }
    ORDER BY ?fechaPrestamo
    """
    sparql = SPARQLWrapper(fuseki_url)
    sparql.setQuery(consulta)
    sparql.setReturnFormat(JSON)
    resultados = sparql.query().convert()
    libros_prestados = [{"titulo": r["titulo"]["value"],
                         "clienteNombre": r["clienteNombre"]["value"],
                         "tipo": r["tipo"]["value"],
                         "fechaPrestamo": r["fechaPrestamo"]["value"],
                         "fechaDevolucion": r["fechaDevolucion"]["value"]} for r in resultados["results"]["bindings"]]
    return templates.TemplateResponse("libros_prestados.html", {"request": request, "libros_prestados": libros_prestados})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)