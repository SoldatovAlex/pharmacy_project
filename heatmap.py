import gmplot
import googlemaps
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats


with open("api_key.txt", "r") as file:
    api_key = file.readline()

gmaps = googlemaps.Client(key=api_key)
hamovniki_coordinates = gmaps.geocode("Хамовники, Москва")

ph_data_path = "pharmacy/data.csv"
try:
    pharmacy_base = pd.read_csv(ph_data_path, sep='\t')
except FileNotFoundError:
    print("К сожалению, файл  отсутствует в директории")

data_path = "result.csv"
try:
    coordinates = pd.read_csv(data_path, sep=',')
except FileNotFoundError:
    print("К сожалению, файл  отсутствует в директории")


def create_heatmap():
    lats = coordinates['CoordinateLan']
    lons = coordinates['CoordinateLng']
    # вот этот лист потом будем передавать для построения тепловой карты. Сейчас там величина P
    relative_values = coordinates["P"].to_list()

    # создаем png
    xmin = lons.min()
    xmax = lons.max()
    ymin = lats.min()
    ymax = lats.max()
    grid_points = 150
    X, Y = np.mgrid[xmin:xmax:complex(grid_points, 1), ymin:ymax:complex(grid_points, 1)]
    positions = np.vstack([X.ravel(), Y.ravel()])
    values = np.vstack([lons, lats])
    kernel = stats.gaussian_kde(values)
    Z = np.reshape(kernel(positions), X.shape)
    Z[Z < 1] = np.nan
    fig = plt.figure(frameon=True)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_aspect('equal')
    ax.set_axis_off()
    ax.tick_params(which='both', direction='in')
    fig.add_axes(ax)
    ax.imshow(np.rot90(Z), cmap='coolwarm', alpha=0.4, extent=[xmin, xmax, ymin, ymax])
    extent = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig('heatmap_doc/heatmap.png', format='png', dpi=1000, transparent=True, bbox_inches=extent, pad_inches=0)

    lon_midpt = np.mean([xmin, xmax])
    lat_midpt = np.mean([ymin, ymax])
    img_bounds = {}
    img_bounds['west'] = (xmin - lon_midpt) * (grid_points / (grid_points - 1)) + lon_midpt
    img_bounds['east'] = (xmax - lon_midpt) * (grid_points / (grid_points - 1)) + lon_midpt
    img_bounds['north'] = (ymax - lat_midpt) * (grid_points / (grid_points - 1)) + lat_midpt
    img_bounds['south'] = (ymin - lat_midpt) * (grid_points / (grid_points - 1)) + lat_midpt


    # создаем объект класса GoogleMapPlotter, это gmaps карта
    gmap = gmplot.GoogleMapPlotter(lat=hamovniki_coordinates[0]['geometry']['location']['lat'],
                                   lng=hamovniki_coordinates[0]['geometry']['location']['lng'],
                                   zoom=14,
                                   apikey=api_key)

    ph_lat = pharmacy_base['lat'].to_list()
    ph_lng = pharmacy_base['lng'].to_list()

    # создаем массив цветов
    colors = []
    for g in range(0, 256):
        colors.append('#%02x%02x%02x' % (255, g, 0))

    for r in range(255, -1, -1):
        colors.append('#%02x%02x%02x' % (r, 255, 0))

    # рисуем маркеры
    for index in range(len(ph_lng)):
        gmap.marker(ph_lat[index], ph_lng[index], color='b')

    # накладываем png на карту
    gmap.ground_overlay('heatmap_doc/heatmap.png', img_bounds)
    # в gmap.scatter relative_values в аргументе color, говорит от том на основании каких данных строим тепловую карту.
    gmap.scatter(lats, lons, color=[colors[int(value * (len(colors) - 1))] for value in relative_values], size=11,
                 marker=False)
    gmap.draw('heatmap_doc/map.html')



create_heatmap()


