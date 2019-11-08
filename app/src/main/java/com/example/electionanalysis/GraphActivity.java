package com.example.electionanalysis;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;

import android.os.Bundle;
import android.util.Log;

import com.github.mikephil.charting.charts.BarChart;
import com.github.mikephil.charting.components.AxisBase;
import com.github.mikephil.charting.components.XAxis;
import com.github.mikephil.charting.data.BarData;
import com.github.mikephil.charting.data.BarDataSet;
import com.github.mikephil.charting.data.BarEntry;
import com.github.mikephil.charting.formatter.IAxisValueFormatter;
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter;

import com.github.mikephil.charting.utils.ColorTemplate;
import com.google.android.gms.tasks.OnCompleteListener;
import com.google.android.gms.tasks.Task;
import com.google.firebase.firestore.DocumentReference;
import com.google.firebase.firestore.DocumentSnapshot;
import com.google.firebase.firestore.FirebaseFirestore;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class GraphActivity extends AppCompatActivity {
    FirebaseFirestore db;
    double bjp,congress,mns,ncp,shivsena,others;
    Map<String,Object > number =new HashMap<>();
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_graph);
        db=FirebaseFirestore.getInstance();
        final DocumentReference docRef=db.collection("data").document("volume");
        Task<DocumentSnapshot> task = docRef.get();
        while(task.isComplete() == false){
            System.out.println("busy wait goals");
        }
        DocumentSnapshot document= task.getResult();
        number = document.getData();

        bjp=(long)number.get("bjp");
        congress=document.getDouble("congress");
        shivsena=document.getDouble("shivsena");
        mns=document.getDouble("mns");
        ncp=document.getDouble("ncp");
        others=document.getDouble("other");
        BarChart chart = findViewById(R.id.barchart);
        System.out.println("Value of bjp"+bjp);
        List<BarEntry> entries = new ArrayList<>();
        entries.add(new BarEntry(1f, (int)bjp));
        entries.add(new BarEntry(2f, (int)congress));
        entries.add(new BarEntry(3f, (int)ncp));
        entries.add(new BarEntry(4f, (int)mns));
        entries.add(new BarEntry(5f, (int)shivsena));


        BarDataSet set = new BarDataSet(entries, "Party based tweets");

        final ArrayList<String> BarEntryLabels = new ArrayList<String>();
        BarEntryLabels.add("BJP");
        BarEntryLabels.add("Congress");
        BarEntryLabels.add("MNS");
        BarEntryLabels.add("NCP");
        BarEntryLabels.add("Shivsena");

        XAxis xAxis = chart.getXAxis();
        xAxis.setGranularity(1f);
        xAxis.setCenterAxisLabels(true);
        xAxis.setLabelRotationAngle(-90);
        xAxis.setPosition(XAxis.XAxisPosition.BOTTOM);
        xAxis.setValueFormatter(new IAxisValueFormatter() {

    public String getFormattedValue(float value, AxisBase axis) {
    if (value >= 0) {
    if (value <= BarEntryLabels.size() - 1) {
    return BarEntryLabels.get((int) value);
    }
    return "";
    }
    return "";
    }
        });
        BarData data = new BarData(set);
        data.setBarWidth(0.9f); // set custom bar width
        chart.setData(data);
        chart.animateY(5000);
        set.setColors(ColorTemplate.COLORFUL_COLORS);
        chart.setFitBars(true); // make the x-axis fit exactly all bars
        chart.invalidate(); //
    }
}
