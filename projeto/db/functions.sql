CREATE OR REPLACE FUNCTION validar_uf(p_uf VARCHAR) 
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (SELECT 1 FROM servidores_ativos WHERE uf = p_uf);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validar_cargo(p_cargo VARCHAR) 
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (SELECT 1 FROM servidores_ativos WHERE cargo = p_cargo);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validar_orgao(p_orgao VARCHAR) 
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (SELECT 1 FROM servidores_ativos WHERE orgao = p_orgao);
END;
$$ LANGUAGE plpgsql;