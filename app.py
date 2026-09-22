"""
Author Network Analysis Application
Приложение для анализа научных сетей авторов через соавторство
"""

from flask import Flask, jsonify, request, render_template
import networkx as nx
from collections import defaultdict
import json

app = Flask(__name__)

# === МОДЕЛЬ ДАННЫХ ===
class AuthorNetwork:
    """Класс для управления сетью авторов и их связями"""
    
    def __init__(self):
        self.graph = nx.Graph()
        self.articles = []
        self.author_stats = defaultdict(lambda: {
            'publications': 0,
            'connections': 0,
            'centrality': 0
        })
    
    def add_article(self, title, authors, year):
        """Добавить статью и связи между авторами"""
        article = {
            'title': title,
            'authors': authors,
            'year': year
        }
        self.articles.append(article)
        
        # Добавляем узлы
        for author in authors:
            self.graph.add_node(author, year=year)
            self.author_stats[author]['publications'] += 1
        
        # Добавляем рёбра (соавторство)
        for i, author1 in enumerate(authors):
            for author2 in authors[i+1:]:
                if self.graph.has_edge(author1, author2):
                    self.graph[author1][author2]['weight'] += 1
                else:
                    self.graph.add_edge(author1, author2, weight=1)
    
    def calculate_metrics(self):
        """Расчёт метрик центральности сети"""
        # Степень центральности
        degree_centrality = nx.degree_centrality(self.graph)
        
        # Центральность по посредничеству (как в статье)
        betweenness_centrality = nx.betweenness_centrality(self.graph, weight='weight')
        
        # Близость
        try:
            closeness_centrality = nx.closeness_centrality(self.graph)
        except:
            closeness_centrality = {}
        
        for author in self.graph.nodes():
            self.author_stats[author]['connections'] = self.graph.degree(author)
            self.author_stats[author]['centrality'] = betweenness_centrality.get(author, 0)
        
        return {
            'degree': degree_centrality,
            'betweenness': betweenness_centrality,
            'closeness': closeness_centrality
        }
    
    def get_graph_json(self):
        """Преобразовать граф в JSON для D3.js визуализации"""
        self.calculate_metrics()
        
        nodes = []
        for node in self.graph.nodes():
            nodes.append({
                'id': node,
                'label': node,
                'size': max(self.author_stats[node]['centrality'] * 100, 5),
                'connections': self.author_stats[node]['connections'],
                'publications': self.author_stats[node]['publications']
            })
        
        links = []
        for source, target, data in self.graph.edges(data=True):
            links.append({
                'source': source,
                'target': target,
                'weight': data.get('weight', 1)
            })
        
        return {
            'nodes': nodes,
            'links': links,
            'stats': {
                'total_authors': len(nodes),
                'total_connections': len(links),
                'network_density': nx.density(self.graph)
            }
        }
    
    def find_communities(self):
        """Найти кластеры авторов (научные школы)"""
        from networkx.algorithms import community
        communities = list(community.greedy_modularity_communities(self.graph))
        return communities


# === ИНИЦИАЛИЗАЦИЯ СЕТИ ===
network = AuthorNetwork()

# Тестовые данные из загруженной статьи
SAMPLE_DATA = [
    {
        'title': 'Сетевой анализ историографии: динамика формирования межрегиональной компоненты сети АИК',
        'authors': ['Гарскова И.М.', 'Бородкин Л.И.', 'Владимиров В.Н.', 'Канищев В.В.'],
        'year': 2017
    },
    {
        'title': 'Многомерный статистический анализ в исторических исследованиях',
        'authors': ['Бородкин Л.И.', 'Изместьева Т.Ф.'],
        'year': 1986
    },
    {
        'title': 'Историческая информатика: Учебное пособие',
        'authors': ['Бородкин Л.И.', 'Гарскова И.М.', 'Бояринцев В.И.'],
        'year': 1996
    },
    {
        'title': 'Компьютерное моделирование исторических процессов',
        'authors': ['Бородкин Л.И.', 'Тяжельникова В.С.'],
        'year': 1995
    },
    {
        'title': 'Историческая геоинформатика: ГИС в исторических исследованиях',
        'authors': ['Владимиров В.Н.', 'Силина И.Г.', 'Колдаков Д.В.'],
        'year': 2005
    },
    {
        'title': 'Социальная история и компьютер',
        'authors': ['Канищев В.В.', 'Кончаков Р.Б.'],
        'year': 1998
    },
    {
        'title': 'Применение ГИС в историко-демографических исследованиях',
        'authors': ['Владимиров В.Н.', 'Канищев В.В.', 'Плодунова В.В.'],
        'year': 2000
    },
    {
        'title': 'Сетевой анализ в исторических исследованиях',
        'authors': ['Бородкин Л.И.', 'Гарскова И.М.', 'Владимиров В.Н.'],
        'year': 2017
    },
]

# Загружаем тестовые данные
for article in SAMPLE_DATA:
    network.add_article(article['title'], article['authors'], article['year'])


# === API ENDPOINTS ===

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/api/graph', methods=['GET'])
def get_graph():
    """Получить данные графа для визуализации"""
    return jsonify(network.get_graph_json())

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Получить список всех статей"""
    return jsonify(network.articles)

@app.route('/api/author/<author_name>', methods=['GET'])
def get_author_info(author_name):
    """Получить информацию об авторе"""
    if author_name not in network.graph:
        return jsonify({'error': 'Author not found'}), 404
    
    neighbors = list(network.graph.neighbors(author_name))
    
    return jsonify({
        'name': author_name,
        'stats': network.author_stats[author_name],
        'collaborators': neighbors,
        'collaborators_count': len(neighbors)
    })

@app.route('/api/communities', methods=['GET'])
def get_communities():
    """Получить научные сообщества (кластеры авторов)"""
    communities = network.find_communities()
    
    communities_data = []
    for i, community in enumerate(communities):
        communities_data.append({
            'id': i,
            'members': list(community),
            'size': len(community)
        })
    
    return jsonify({'communities': communities_data})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Получить статистику сети"""
    graph_data = network.get_graph_json()
    
    return jsonify({
        'total_authors': graph_data['stats']['total_authors'],
        'total_connections': graph_data['stats']['total_connections'],
        'network_density': graph_data['stats']['network_density'],
        'total_articles': len(network.articles),
        'average_collaborators': (graph_data['stats']['total_connections'] * 2) / graph_data['stats']['total_authors'] if graph_data['stats']['total_authors'] > 0 else 0
    })

@app.route('/api/upload', methods=['POST'])
def upload_article():
    """Добавить новую статью"""
    data = request.json
    
    try:
        network.add_article(
            data['title'],
            data['authors'],
            data.get('year', 2024)
        )
        return jsonify({'status': 'success', 'message': 'Article added'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000)