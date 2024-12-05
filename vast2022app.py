import pandas as pd
import os
import dash
from dash import Dash, dcc, html, Input, Output
import plotly.express as px
import plotly.graph_objects as go
import dash_cytoscape as cyto

# Load pickled data for faster loading (previously processed data)
dfParticipantStatusLogs = pd.read_pickle('processed_participant_status_logs.pkl')
attributes = {file: pd.read_pickle(f'processed_{file}_attributes.pkl') for file in os.listdir('Datasets/Attributes') if file.endswith('.csv')}
journals = {file: pd.read_pickle(f'processed_{file}_journals.pkl') for file in os.listdir('Datasets/Journals') if file.endswith('.csv')}

# Calculate additional metrics
householdKidCounts = pd.read_pickle('processed_household_kid_counts.pkl')
kidCounts = attributes["Participants.csv"]["haveKids"].value_counts()
dfAgeVsIncome = attributes["Participants.csv"].merge(journals["FinancialJournal.csv"], on='participantId')
dfAgeVsIncome = dfAgeVsIncome.loc[dfAgeVsIncome["category"] == "Wage"]
attributes["Participants.csv"]["ageGroup"] = pd.cut(attributes["Participants.csv"]["age"], bins=[20, 30, 40, 50], labels=["20-29", "30-39", "40-49"])
pivotDf = attributes["Participants.csv"].pivot_table(index='ageGroup', columns='educationLevel', aggfunc='size', fill_value=0, observed=False).reset_index()

# Aggregate edges to count how many times participants have communicated
edgesWithFrequency = (journals["SocialNetwork.csv"].groupby(['participantIdFrom', 'participantIdTo']).size().reset_index(name='weight'))

# Aggregate total interactions per participant to find top participants
participantInteractions = (edgesWithFrequency.groupby('participantIdFrom')['weight'].sum().reset_index().rename(columns={'participantIdFrom': 'participantId', 'weight': 'totalWeight'}))

# Select the top 100 participants based on interaction frequency (adjust as needed)
topParticipants = participantInteractions.nlargest(10, 'totalWeight')['participantId']

# Filter edges to include only those involving the top participants
filteredEdges = edgesWithFrequency[
	edgesWithFrequency['participantIdFrom'].isin(topParticipants) | edgesWithFrequency['participantIdTo'].isin(topParticipants)
]

filteredEdges = filteredEdges.loc[filteredEdges['weight'] > 200]

# Create nodes (unique participant IDs in the filtered edges)
nodes = set(filteredEdges['participantIdFrom']).union(set(filteredEdges['participantIdTo']))
elements = [{"data": {"id": str(node), "label": f"Participant {node}"}} for node in nodes]

# Create edges with frequency
edges = [
	{"data": {"source": str(row["participantIdFrom"]), "target": str(row["participantIdTo"]), "weight": row["weight"]}}
	for _, row in filteredEdges.iterrows()
]

# Combine nodes and edges into the elements list
elements.extend(edges)

interactionsByDay = journals["SocialNetwork.csv"].groupby(journals["SocialNetwork.csv"]['timestamp'].dt.date).size().reset_index(name='interactionCount')

degreeCounts = attributes["Jobs.csv"]["educationRequirement"].value_counts().reset_index()
degreeCounts.columns = ["educationRequirement", "count"]

apartmentLocation = attributes["Apartments.csv"][["location"]]
apartmentLocation["buildingType"] = "apartment"

pubLocation = attributes["Pubs.csv"][["location"]]
pubLocation["buildingType"] = "pub"

restaurantLocation = attributes["Restaurants.csv"][["location"]]
restaurantLocation["buildingType"] = "restaurant"

schoolLocation = attributes["Schools.csv"][["location"]]
schoolLocation["buildingType"] = "school"

combined = pd.concat([apartmentLocation, pubLocation, restaurantLocation, schoolLocation], ignore_index=True)

# Remove 'POINT(' and ')' and split the coordinates
combined["location_clean"] = combined["location"].str.strip("POINT ()")

# Split the cleaned location into x and y coordinates
combined["x"] = combined["location_clean"].str.split(" ").str[0].astype(float)
combined["y"] = combined["location_clean"].str.split(" ").str[1].astype(float)

# Keep only relevant columns
finalDf = combined[["x", "y", "buildingType"]]

# Initialize Dash app
app = Dash(__name__)
colorSequence = px.colors.qualitative.Set1
buildingTypes = finalDf["buildingType"].unique()
colorMap = {buildingType: colorSequence[i % len(colorSequence)] for i, buildingType in enumerate(buildingTypes)}

# Layout with dcc.Store to store cleaned data
app.layout = html.Div([
	dcc.Store(id="cleanedDataStore", data={
		"householdKidCounts": householdKidCounts.to_dict('records'),
		"kidCounts": kidCounts.to_dict(),
		"dfAgeVsIncome": dfAgeVsIncome.to_dict('records'),
		"pivotDf": pivotDf.to_dict('records')
	}),

	# Home Page layout
	dcc.Location(id="url", refresh=False),
	html.Div(id="pageContent")
])

# Home page layout
homePage = html.Div([
	html.H1("Welcome to the Data Insights Dashboard 🚀"),

	html.P("""
		Alright, here’s the deal: this dashboard is all about making sense of data in a way that actually makes sense. 
		We’re looking at stuff like age, income, social connections, and even business locations. It’s kind of like 
		the ultimate behind-the-scenes look at how people live, work, and connect.
	"""),

	html.P("""
		Here’s what you can dive into:
	"""),
	html.Ul([
		html.Li("📊 **Participant Dashboard**: Get the lowdown on age groups, who has kids, how much people are making, and education stats."),
		html.Li("🌐 **Social Activity Dashboard**: Find out who’s connecting with who, how often, and how that changes over time."),
		html.Li("🏙️ **Business Dashboard**: See what kinds of jobs people have and where businesses are located around the city.")
	]),

	html.P("""
		Use the links below to check out each dashboard. It’s all set up to help you explore the data and maybe 
		even find a few surprises along the way.
	"""),

	dcc.Link("Participant Dashboard", href="/participantDashboard"),
	html.Br(),
	dcc.Link("Social Activity Dashboard", href="/socialActivityDashboard"),
	html.Br(),
	dcc.Link("Business Dashboard", href="/businessDashboard")
])


# Participant Dashboard layout
participantDashboardLayout = html.Div([
	html.H1("Participant Dashboard 📊"),

	dcc.Graph(
		figure=px.bar(
			x=["Without Kids", "With Kids"],
			y=[kidCounts.get(0, 0), kidCounts.get(1, 0)],
			labels={"x": "Presence of Kids", "y": "Number of Participants"},
			title="Participants with/without Kids",
			color_discrete_sequence=[colorSequence[1]]
		).update_traces(
			marker=dict(
				line=dict(
					color="black",
					width=2
				)
			)
		)
	),
	html.P("""
		No shocker here—most participants don’t have kids. About 70% are kid-free, which makes sense since we’re probably 
		looking at a younger, working-age crowd. This is good info for figuring out where family-focused services or 
		policies might (or might not) be needed.
	"""),

	dcc.Graph(
		id="ageHistogram",
		figure=px.histogram(
			attributes["Participants.csv"],
			x="age",
			nbins=8,
			title="Age Distribution",
			labels={"age": "Age", "count": "Frequency"},
			color_discrete_sequence=[colorSequence[1]]
		).update_traces(
			marker=dict(
				line=dict(
					color="black",
					width=2
				)
			)
		)
	),
	html.P("""
		The age breakdown is pretty balanced, but the 30-40 age group definitely takes the top spot. This makes sense—these are 
		prime working years, and maybe even family-building years. Whatever the case, this group’s decisions are likely driving 
		a lot of the trends we see.
	"""),

	dcc.Graph(
		id="scatterAgeIncome",
		figure=px.scatter(
			dfAgeVsIncome,
			x="age",
			y="amount",
			color="age",
			title="Age vs. Income",
			labels={"age": "Age", "amount": "Income"},
			color_continuous_scale=colorSequence
		)
	),
	html.P("""
		Here’s where it gets interesting: income goes up with age (no surprise there), but look at the spread in the middle 
		years. People in their 30s and 40s are all over the place when it comes to income, which probably reflects career 
		progression—or lack of it—for some folks. There’s a lot to dig into here.
	"""),

	dcc.Graph(
		id="householdVsKidSize",
		figure=px.bar(
			householdKidCounts,
			x="householdSize",
			y="count",
			color="haveKids",
			title="Household Size vs. Presence of Kids",
			labels={"householdSize": "Household Size", "count": "Number of Participants"},
			color_discrete_sequence=colorSequence,
			barmode="group"
		).update_traces(
			marker=dict(
				line=dict(
					color="black",
					width=2
				)
			)
		)
	),
	html.P("""
		No surprises here—larger households are more likely to have kids, while smaller households (1-2 people) 
		are mostly kid-free. This is the kind of straightforward insight that helps when planning housing, 
		community services, or even marketing campaigns.
	"""),

	dcc.Graph(
		id="barEducationAge",
		figure=px.bar(
			pivotDf.reset_index(),
			x="ageGroup",
			y=pivotDf.columns[1:],
			title="Education Levels within Age Groups",
			labels={"value": "Number of Participants", "ageGroup": "Age Group"},
			barmode="group",
			color_discrete_sequence=colorSequence,
			category_orders={"ageGroup": pivotDf["ageGroup"].tolist()}
		).update_traces(
			marker=dict(
				line=dict(
					color="black",
					width=2
				)
			)
		)
	),
	html.P("""
		Across the board, High School/College-level education dominates. Younger participants seem to be 
		catching up with higher education, which could point to a shift toward more specialized skill sets 
		in the future. It’s definitely something to keep an eye on.
	"""),

	dcc.Link("Home Page", href="/"),
	html.Br(),
	dcc.Link("Social Activity Dashboard", href="/socialActivityDashboard"),
	html.Br(),
	dcc.Link("Business Dashboard", href="/businessDashboard")
])
		


# Social Activity Dashboard layout
socialActivityDashboardLayout = html.Div([
	html.H1("Social Activity Dashboard 🌐"),

	cyto.Cytoscape(
		id="cytoscapeSocialNetwork",
		layout={"name": "cose"},
		style={"width": "100%", "height": "600px", "avoidOverlap": True},
		elements=elements,
		stylesheet=[
			{
				"selector": "node",
				"style": {
					"label": "data(label)",
					"width": 30,
					"height": 30,
					"background-color": "#0074D9",
					"color": "black",
					"text-valign": "center",
					"text-halign": "center",
					"font-size": "10px",
				}
			},
			{
				"selector": "edge",
				"style": {
					"width": 3,
					"line-color": "#87CEEB",
					"target-arrow-color": "#87CEEB",
					"target-arrow-shape": "triangle",
				}
			}
		]
	),
	html.P("""
		This network map is like a snapshot of who’s talking to who. Big clusters show active groups or 
		influencers, while the solo dots might be people on the outskirts who aren’t engaging as much. 
		Great for spotting opportunities to boost participation.
	"""),

	dcc.Graph(
		id="interactionTimeline",
		figure=px.line(
			interactionsByDay,
			x='timestamp',
			y='interactionCount',
			title="Timeline of Interactions",
			labels={"timestamp": "Date", "interactionCount": "Number of Interactions"},
			line_shape='linear'
		).update_traces(
			line=dict(color='royalblue')
		)
	),
	html.P("""
		Here’s the timeline. Interaction levels keep climbing, which is awesome, but check out those peaks— 
		likely events or campaigns that really got people talking. This is where you’d want to focus your 
		energy to keep the momentum going.
	"""),

	dcc.Link("Home Page", href="/"),
	html.Br(),
	dcc.Link("Participant Dashboard", href="/participantDashboard"),
	html.Br(),
	dcc.Link("Business Dashboard", href="/businessDashboard")
])


# Business Dashboard layout
businessDashboard = html.Div([
	html.H1("Business Dashboard 🏙️"),

	dcc.Graph(
		id="employmentByIndustry",
		figure=px.pie(
			degreeCounts,
			values="count",
			names="educationRequirement",
			title="Employment by Education"
		)
	),
	html.P("""
		Most jobs are filled by people with High School or College-level education—no surprise there. 
		Graduate-level roles make up a smaller chunk, which might mean fewer opportunities for highly 
		specialized skills. That could be worth digging into for workforce planning.
	"""),

	dcc.Graph(
		figure=go.Figure(
			data=go.Scatter(
				x=finalDf["x"],
				y=finalDf["y"],
				mode="markers",
				marker=dict(
					size=8,
					color=[colorMap[buildingType] for buildingType in finalDf["buildingType"]],
					line=dict(
						width=1,
						color="black"
					)
				),
				text=finalDf["buildingType"]
			),
			layout=go.Layout(
				title="Business Types in the City",
				margin=dict(l=0, r=0, t=0, b=0),
				xaxis=dict(range=[finalDf['x'].min(), finalDf['x'].max()], showgrid=False),
				yaxis=dict(range=[finalDf['y'].min(), finalDf['y'].max()], showgrid=False, scaleanchor='x', scaleratio=1)
			)
		)
	),
	html.P("""
		Here’s the city map showing where businesses are clustered. Apartments, restaurants, pubs, and schools 
		all have their own zones, but you can see some overlap in busier areas. This kind of info is huge for 
		planning new businesses or even improving city infrastructure.
	"""),

	dcc.Link("Home Page", href="/"),
	html.Br(),
	dcc.Link("Participant Dashboard", href="/participantDashboard"),
	html.Br(),
	dcc.Link("Social Activity Dashboard", href="/socialActivityDashboard")
])


# Callback to update pages based on the URL
@app.callback(
	Output("pageContent", "children"),
	Input("url", "pathname")
)
def displayPage(pathname):
	if pathname == "/participantDashboard":
		return participantDashboardLayout
	elif pathname == "/socialActivityDashboard":
		return socialActivityDashboardLayout
	elif pathname == "/businessDashboard":
		return businessDashboard
	else:
		return homePage

# Run server
if __name__ == "__main__":
	app.run_server(debug=True)
