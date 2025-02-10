#!/bin/bash
# Script para criar o arquivo .envrc que ativa um ambiente Conda com Direnv

# Verifica se o comando 'conda' está disponível
if ! command -v conda &> /dev/null; then
  echo "Erro: o comando 'conda' não foi encontrado. Certifique-se de que o Conda está instalado e no PATH."
  exit 1
fi

# Pergunta qual o nome do ambiente Conda a ser ativado
echo "Digite o nome do ambiente Conda que deseja ativar:"
read -r CONDA_ENV

# Verifica se algum valor foi informado
if [[ -z "$CONDA_ENV" ]]; then
  echo "Nenhum ambiente informado. Abortando."
  exit 1
fi

# Obtém o diretório base da instalação do Conda
CONDA_BASE=$(conda info --base)

# Cria o arquivo .envrc com o conteúdo apropriado
cat <<EOF > .envrc
#!/bin/bash
# Carrega as funções do Conda para que 'conda activate' funcione
source "\$(conda info --base)/etc/profile.d/conda.sh"
# Ativa o ambiente Conda informado
conda activate $CONDA_ENV
EOF

direnv allow

echo "Arquivo .envrc criado com sucesso no diretório $(pwd)!"
echo "Agora, execute 'direnv allow' para autorizar a execução do .envrc."

