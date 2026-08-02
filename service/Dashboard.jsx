import { useEffect, useState } from "react";
import api from "../services/api";

export default function Dashboard() {

    const [status, setStatus] = useState("Carregando...");

    useEffect(() => {

        api.get("/api/session-check")
            .then((r) => {
                setStatus(r.data.logged ? "Logado" : "Não Logado");
            })
            .catch(() => {
                setStatus("Erro Backend");
            });

    }, []);

    return (

        <div style={{padding:40}}>

            <h1>VÉRTICE IA</h1>

            <h2>{status}</h2>

        </div>

    );

}